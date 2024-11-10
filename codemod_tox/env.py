from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Generator

from .base import ToxBase
from .exceptions import HoistError, ParseError
from .options import ToxOptions
from .parse import TOX_ENV_TOKEN_RE


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
