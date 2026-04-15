from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Generator

from .base import ToxBase
from .exceptions import HoistError, NoFactorMatch, ParseError
from .options import ToxOptions
from .parse import TOX_ENV_TOKEN_RE
from .utils import pre_num_suf


def _split_top_level(s: str) -> list[str]:
    """Split s on dashes that are not inside curly braces."""
    parts = []
    depth = 0
    start = 0
    for i, c in enumerate(s):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "-" and depth == 0:
            parts.append(s[start:i])
            start = i + 1
    parts.append(s[start:])
    return parts


@dataclass(frozen=True)
class ToxEnv(ToxBase):
    """
    A single piece of an envlist, possibly generative.

    e.g. `py{37,38}-tests` or `{a,b}-{c,d}`
    """

    pieces: tuple[ToxOptions | str, ...]

    def __iter__(self) -> Generator[str, None, None]:
        locations = [
            (i, f.options)
            for (i, f) in enumerate(self.pieces)
            if isinstance(f, ToxOptions)
        ]
        if not locations:
            # only literals, if there aren't locations
            yield "".join(self.pieces)  # type: ignore[arg-type]
        else:
            option_locations, option_inputs = list(
                zip(
                    *[
                        (i, f.options)
                        for (i, f) in enumerate(self.pieces)
                        if isinstance(f, ToxOptions)
                    ]
                )
            )
            for p in product(*option_inputs):
                r = dict(zip(option_locations, p))
                yield "".join([r.get(i, x) for i, x in enumerate(self.pieces)])

    def matches(self, other: str) -> bool:
        factors = set(other.split("-"))
        return self.map_any(other.__eq__) or self.map_any(
            lambda x: bool(factors & set(x.split("-")))
        )

    def common_factors(self) -> set[str]:
        """
        Returns the set of factors contained in all envs
        """
        working_set: set[str] | None = None
        for env in self:
            factors = set(env.split("-"))
            if working_set is None:
                working_set = factors
            else:
                working_set &= factors
        assert working_set is not None
        return working_set

    def hoist(self, prefix: str) -> "ToxEnv":
        """
        Moves a common prefix from options into a string.
        """
        new_pieces: list[ToxOptions | str] = []
        for i, o in enumerate(self.pieces):
            if isinstance(o, str):
                if o.startswith(prefix):  # len(o) >= len(prefix); we're done
                    new_pieces.extend(self.pieces[i:])
                    break
                elif prefix.startswith(o):  # len(prefix) >= len(o)
                    prefix = prefix[len(o) :]
                    new_pieces.append(o)
                else:
                    raise HoistError(f"{o!r} cannot take {prefix!r}")
            else:
                assert isinstance(o, ToxOptions)
                if o.startswith(prefix):
                    new_o = o.removeprefix(prefix)
                    # TODO if new_pieces and new_pieces[-1] is str new_pieces[-1] += prefix
                    new_pieces.append(prefix)
                    if new_o:
                        new_pieces.append(new_o)
                    new_pieces.extend(self.pieces[i + 1 :])
                    break
                else:
                    # The only time this is likely to help is with degenerate
                    # options like those that are unnecessary like {x} [no
                    # comma] or {x,x} (duplicated)
                    c = o.common_prefix()
                    com = min(len(c), len(prefix))
                    if c[:com] == prefix[:com]:
                        new_o = o.removeprefix(c[:com])
                        if not new_o:
                            new_pieces.append(c[:com])
                            prefix = prefix[com:]
                        else:
                            raise HoistError(f"Leftover nonmatched {prefix!r}")
                    else:
                        raise HoistError(f"{o!r} cannot take {prefix!r}")
        else:
            raise HoistError("Ran off end of pieces")
        return self.__class__(tuple(new_pieces))

    def _bucket(self) -> tuple[str, ToxOptions, str]:
        """
        If this Env is a simple enough expression, break it into pieces.

        For `py{38,39}-tests` will return `("py", ToxOptions(("38", "39")),
        "-tests")` -- that is, a left and right literal, and an option in the
        middle.  If this consists only of a literal, the middle and right ones
        will be falsy (but not None).

        Otherwise raises `HoistError`.
        """
        left: str = ""
        middle = ToxOptions(("",))
        right: str = ""

        for p in self.pieces:
            if isinstance(p, str):
                if middle:
                    right += p
                else:
                    left += p
            else:
                try:
                    one = p.one()
                except ValueError:
                    if middle:
                        raise HoistError(">1 ToxOption involved")
                    middle = p  # frozen, so this is fine
                else:
                    if middle:
                        right += one
                    else:
                        left += one

        return (left, middle, right)

    def _add_number_to_factor(self, value: str) -> "ToxEnv | None":
        """Try to add value's numeric part to a single factor's ToxOptions.

        self must be a single factor (no dashes).  Returns None if the
        factor and value don't share a common prefix with numeric suffixes
        in both.  For example, factor "py3{9,10}" matches value "py311"
        (prefix "py3", suffixes "9"/"10"/"11" are all numeric), but
        factor "foo{3,4}" does not match value "py311".

        Suffixes must also match.
        """
        if (pns := pre_num_suf(value)) is None:
            return None
        vpre, vnum, vsuf = pns
        if not vpre:
            return None
        epres = {vpre}
        enums = {vnum}
        esufs = {vsuf}
        for env in self:
            pns = pre_num_suf(env)
            if pns is None:
                return None
            epres.add(pns[0])
            enums.add(pns[1])
            esufs.add(pns[2])
        if len(epres) != 1 or len(esufs) != 1:
            # The prefixes or suffixes don't all match, nothing we can do.
            return None

        # See if we can keep the original fixed part.
        assert isinstance(self.pieces[0], str)
        new_pre = vpre
        new_nums = sorted(enums, key=int)
        if (pns := pre_num_suf(self.pieces[0])) is not None:
            prefix_num = pns[1]
            # Look at the original prefix broken into pre/num/suf. "py3" is
            # nice to keep. `prefix_num` is the "3" in that case, so check if
            # it's just one character and is a valid prefix.
            if len(prefix_num) == 1 and all(n.startswith(prefix_num) for n in new_nums):
                new_nums = [n[1:] for n in new_nums]
                new_pre = self.pieces[0]

        nums = ToxOptions(tuple(new_nums))
        pieces: list[ToxOptions | str] = [x for x in (new_pre, nums, vsuf) if x]  # type: ignore
        return self.__class__(tuple(pieces))

    def add_numeric_option(self, value: str) -> "ToxEnv":
        """
        Adds a new environment to the matching option group.

        The variable part must be numeric: both the existing options and the
        new suffix must be all digits.  Raises ValueError if no matching
        numeric factor is found.
        """
        factors = _split_top_level(str(self))
        for fi, factor_str in enumerate(factors):
            result = ToxEnv.parse(factor_str)._add_number_to_factor(value)
            if result is not None:
                factors[fi] = str(result)
                return ToxEnv.parse("-".join(factors))

        # The factor-split approach iterates all generated strings (e.g., "py38-flask"),
        # which pre_num_suf can't parse because of the dash.  Fall back to scanning
        # pieces directly to find the numeric ToxOptions.
        if (pns := pre_num_suf(value)) is not None:
            vpre, vnum, vsuf = pns
            if vpre:
                new_pieces = list(self.pieces)
                acc = ""
                for pi, piece in enumerate(new_pieces):
                    if isinstance(piece, str):
                        acc += piece
                    elif acc == vpre and all(opt.isdigit() for opt in piece.options):
                        next_literal = ""
                        if pi + 1 < len(new_pieces) and isinstance(
                            new_pieces[pi + 1], str
                        ):
                            next_literal = new_pieces[pi + 1]  # type: ignore[assignment]
                        if next_literal == vsuf:
                            new_opts = tuple(sorted(piece.options + (vnum,), key=int))
                            new_pieces[pi] = ToxOptions(new_opts)
                            return ToxEnv(tuple(new_pieces))

        raise NoFactorMatch(f"No numeric factor in {str(self)!r} matches {value!r}")

    def __or__(self, value: str) -> "ToxEnv":
        """
        Adds this match, may reformat where curlies end up.
        """
        left, middle, right = self._bucket()

        # When this loop exits, `i` is the number of prefix-match characters,
        # up to `len(left)`.
        for i in range(len(value)):
            if i >= len(left):
                break
            if value[i] != left[i]:
                break
        else:
            i = len(value)

        # For single-literal envs, there is no middle, so scooch any
        # non-prefix-matched piece over to the right before checking for suffix
        # matches.
        if not middle and not right:
            left, right = left[:i], left[i:]
        # When this loop exits, `j` is the number of suffix-match characters,
        # up to `len(right)`.
        for j in range(len(value)):
            if j >= len(right):
                break
            if i + j >= len(value):
                break
            if value[-j - 1] != right[-j - 1]:
                break
        else:
            j = len(value)

        # N.b. Have to be careful because j can be zero
        left, middle = left[:i], middle.addprefix(left[i:])
        middle, right = (
            middle.addsuffix(right[: len(right) - j]),
            right[len(right) - j :],
        )
        value = value[i : len(value) - j]

        middle = ToxOptions(middle.options + (value,))
        pieces: list[ToxOptions | str] = [x for x in (left, middle, right) if x]  # type: ignore
        return self.__class__(tuple(pieces))

    @classmethod
    def parse(self, s: str) -> "ToxEnv":
        pieces: list[ToxOptions | str] = []
        for match in TOX_ENV_TOKEN_RE.finditer(s):
            if match.group("options"):
                pieces.append(ToxOptions.parse(match.group("options")))
            elif match.group("literal"):
                pieces.append(match.group("literal"))
            else:  # pragma: no cover
                raise ParseError(f"Bad match {match!r}")
        return ToxEnv(tuple(pieces))

    def __str__(self) -> str:
        return "".join(map(str, self.pieces))
