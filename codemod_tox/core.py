from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Generator, Optional

from .exceptions import HoistError, ParseError
from .parse import TOX_ENV_TOKEN_RE
from .utils import _common_prefix, _marklast


class ToxBase:
    def all(self) -> Generator[str, None, None]:  # pragma: no cover
        raise NotImplementedError

    def predicate(self, func: Callable[[str], bool]) -> bool:
        for x in self.all():
            if not func(x):
                return False
        return True

    def only(self, value: str) -> bool:
        """
        Returns whether all possibilities are exactly `value`.

        This is mostly a demonstration, you can also use `.one() == value`
        """
        return self.predicate(value.__eq__)

    def startswith(self, prefix: str) -> bool:
        """
        Returns whether all possibilities start with `prefix`.
        """
        return self.predicate(lambda s: s.startswith(prefix))

    def endswith(self, suffix: str) -> bool:
        """
        Returns whether all possibilities end with `suffix`.
        """
        return self.predicate(lambda s: s.endswith(suffix))

    def __bool__(self) -> bool:
        return any(self.all())

    def common_prefix(self) -> str:
        prev = None
        for env in self.all():
            if prev is None:
                prev = env
            else:
                prev = _common_prefix(env, prev)
        assert prev is not None  # 0 options?
        return prev

    def one(self) -> str:
        """
        Returns the string if only one string matches
        """
        s = set(self.all())
        if len(s) == 1:
            return list(s)[0]
        raise ValueError("Multiple matches")

    @classmethod
    def parse(cls, s: str) -> "ToxBase":  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class ToxOptions(ToxBase):
    """
    A "generative" piece of a tox env name.

    These work differently than shell expansion, and notably can't be nested.
    Whitespace is ignored when parsing, but always output without it.

    e.g. `{a , b }` -> `{a,b}`
    """

    options: tuple[str, ...]

    def all(self) -> Generator[str, None, None]:
        yield from self.options

    def addprefix(self, prefix: str) -> "ToxOptions":
        return self.__class__(tuple(prefix + x for x in self.options))

    def removeprefix(self, prefix: str) -> "ToxOptions":
        assert self.startswith(prefix)
        return self.__class__(tuple(x[len(prefix) :] for x in self.options))

    def addsuffix(self, suffix: str) -> "ToxOptions":
        return self.__class__(tuple(x + suffix for x in self.options))

    def removesuffix(self, suffix: str) -> "ToxOptions":
        assert suffix
        assert self.endswith(suffix)
        return self.__class__(tuple(x[: -len(suffix)] for x in self.options))

    @classmethod
    def parse(self, s: str) -> "ToxOptions":
        assert s[0] == "{"
        assert s[-1] == "}"
        return ToxOptions(tuple(i.strip() for i in s[1:-1].split(",")))

    def __str__(self) -> str:
        return "{%s}" % ",".join(self.options)


@dataclass(frozen=True)
class ToxEnv(ToxBase):
    """
    A single piece of an envlist, possibly generative.

    e.g. `py{37,38}-tests` or `{a,b}-{c,d}`
    """

    pieces: tuple[ToxOptions | str, ...]

    def all(self) -> Generator[str, None, None]:
        locations = [
            (i, f.options)
            for (i, f) in enumerate(self.pieces)
            if isinstance(f, ToxOptions)
        ]
        if not locations:
            # only literals, if there aren't locations
            yield "".join(self.pieces)  # type: ignore[arg-type]
        else:
            factor_locations, factor_inputs = list(
                zip(
                    *[
                        (i, f.options)
                        for (i, f) in enumerate(self.pieces)
                        if isinstance(f, ToxOptions)
                    ]
                )
            )
            for p in product(*factor_inputs):
                r = dict(zip(factor_locations, p))
                yield "".join([r.get(i, x) for i, x in enumerate(self.pieces)])

    def common_factors(self) -> set[str]:
        """
        Returns the set of factors contained in all envs
        """
        working_set: set[str] | None = None
        for env in self.all():
            factors = set(env.split("-"))
            if working_set is None:
                working_set = factors
            else:
                working_set &= factors
        assert working_set is not None
        return working_set

    def _bucket(self) -> tuple[str, Optional[ToxOptions], str]:
        """
        Split the ToxEnv into

        literal, [option, literal]
        """
        left: str = ""
        middle = None
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
                    middle = p  # TODO copy?
                else:
                    if middle:
                        right += one
                    else:
                        left += one

        return (left, middle, right)

    def hoist(self, prefix: str) -> "ToxEnv":
        try:
            return self._hoist_simple(prefix)
        except HoistError:
            return self._hoist_difficult(prefix)

    def _hoist_simple(self, prefix: str) -> "ToxEnv":
        """
        Like hoist but only works on a bucketed env
        """
        left, middle, right = self._bucket()
        if middle is None:
            middle = ToxOptions(("",))
        if not left.startswith(prefix):
            raise HoistError("Does not start with prefix")
        pos = len(prefix)
        left, middle = left[:pos], middle.addprefix(left[pos:])
        candidates: list[ToxOptions | str] = [x for x in (left, middle, right) if x]  # type: ignore
        return self.__class__(tuple(candidates))

    def _hoist_difficult(self, prefix: str) -> "ToxEnv":
        """
        Moves a common prefix from options into a string.
        """
        if not self.startswith(prefix):
            raise HoistError("Does not start with prefix")
        new_pieces: list[ToxOptions | str] = []
        it = iter(self.pieces)
        for p in it:
            if p.startswith(prefix):
                # need to split
                new_pieces.append(prefix)
                rest = p.removeprefix(prefix)
                if rest:
                    new_pieces.append(rest)
                break
            elif isinstance(p, str):
                if prefix.startswith(p):
                    new_pieces.append(p)
                    prefix = prefix.removeprefix(p)
                else:
                    raise HoistError("Unexpected 1")
            else:
                assert isinstance(p, ToxOptions)
                try:
                    one = p.one()
                except ValueError:
                    raise HoistError("Unexpected 2")
                else:
                    new_pieces.append(one)
                    prefix = prefix.removeprefix(one)
                    if not prefix:
                        break
        new_pieces.extend(x for x in it if x)
        return self.__class__(tuple(new_pieces))

    def add(self, value: str) -> "ToxEnv":
        """
        Modifies in place
        """
        left, middle, right = self._bucket()
        if middle is None:
            middle = ToxOptions(("",))

        for i in range(len(value)):
            if i >= len(left):
                break
            if value[i] != left[i]:
                break
        else:
            i = len(value)

        for j in range(len(value) - i):
            if j >= len(right):
                break
            if value[-j - 1] != right[-j - 1]:
                break
        else:
            j = len(right)

        # N.b. Have to be careful because j can be zero
        left, middle = left[:i], middle.addprefix(left[i:])
        middle, right = (
            middle.addsuffix(right[: len(right) - j]),
            right[len(right) - j :],
        )
        value = value[i : len(value) - j]

        middle = ToxOptions(middle.options + (value,))
        return self.__class__((left, middle, right))

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


@dataclass(frozen=True)
class ToxEnvlist(ToxBase):
    """
    An envlist.

    e.g. `py{37,38}-tests, coverage, lint`

    Although both comma and newline separated are supported during parsing,
    only newline separated will be output with `str()`.  Check that
    set(a.all()) != set(b.all()) before changing a configuration value to avoid
    (one-time) churn.
    """

    envs: tuple[ToxEnv, ...]

    def all(self) -> Generator[str, None, None]:
        for e in self.envs:
            yield from e.all()

    @classmethod
    def parse(cls, s: str) -> "ToxEnvlist":
        pieces = []
        buf = ""

        for match in TOX_ENV_TOKEN_RE.finditer(s):
            # This will double-parse but these strings are typically pretty
            # trivial and we've restricted the character set significantly so
            # this should be roughly linear
            if match.group("comma") or match.group("newline"):
                assert buf
                pieces.append(ToxEnv.parse(buf))
                buf = ""
            elif match.group("space"):
                pass
            else:
                buf += match.group(0)

        if buf:
            pieces.append(ToxEnv.parse(buf))

        return cls(tuple(pieces))

    def __str__(self) -> str:
        buf = ""
        default_suffix = "\n"

        for item, last in _marklast(self.envs):
            buf += str(item)
            if not last:
                buf += default_suffix
        return buf
