from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Generator

from .exceptions import HoistError, ParseError
from .parse import TOX_ENV_TOKEN_RE
from .utils import _common_prefix, _marklast


class ToxBase:
    def all(self) -> Generator[str, None, None]:  # pragma: no cover
        raise NotImplementedError

    def startswith(self, prefix: str) -> bool:
        """
        Returns whether all possibilities start with `prefix`.
        """
        for x in self.all():
            if not x.startswith(prefix):
                return False
        return True

    def empty(self) -> bool:
        return not any(self.all())

    def common_prefix(self) -> str:
        prev = None
        for env in self.all():
            if prev is None:
                prev = env
            else:
                prev = _common_prefix(env, prev)
        assert prev is not None  # 0 options?
        return prev

    @classmethod
    def parse(cls, s: str) -> "ToxBase":  # pragma: no cover
        raise NotImplementedError


@dataclass
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

    def removeprefix(self, prefix: str) -> "ToxOptions":
        assert self.startswith(prefix)
        return self.__class__(tuple(x[len(prefix) :] for x in self.options))

    @classmethod
    def parse(self, s: str) -> "ToxOptions":
        assert s[0] == "{"
        assert s[-1] == "}"
        return ToxOptions(tuple(i.strip() for i in s[1:-1].split(",")))

    def __str__(self) -> str:
        return "{%s}" % ",".join(self.options)


@dataclass
class ToxEnv:
    """
    A single piece of an envlist, possibly generative.

    e.g. `py{37,38}-tests` or `{a,b}-{c,d}`
    """

    pieces: list[ToxOptions | str]

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

    def hoist(self, prefix: str) -> "ToxEnv":
        """
        Moves a common prefix from options into a string.
        """
        new_pieces = []
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
                    if not new_o.empty():
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
                        if new_o.empty():
                            new_pieces.append(c[:com])
                            prefix = prefix[com:]
                        else:
                            raise HoistError(f"Leftover nonmatched {prefix!r}")
                    else:
                        raise HoistError(f"{o!r} cannot take {prefix!r}")
        else:
            raise HoistError("Ran off end of pieces")
        return self.__class__(new_pieces)

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
        return ToxEnv(pieces)

    def __str__(self) -> str:
        return "".join(map(str, self.pieces))


@dataclass
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
