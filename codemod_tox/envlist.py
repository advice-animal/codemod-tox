from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generator, Optional

from .base import ToxBase
from .env import ToxEnv
from .exceptions import NoMatch
from .parse import TOX_ENV_TOKEN_RE


@dataclass(frozen=True)
class ToxEnvlist(ToxBase):
    """
    An envlist.

    e.g. `py{37,38}-tests, coverage, lint`

    Although both comma and newline separated are supported during parsing,
    only newline separated will be output with `str()`.  Check that
    set(a) != set(b) before changing a configuration value to avoid
    (one-time) churn.
    """

    envs: tuple[ToxEnv, ...]

    def __iter__(self) -> Generator[str, None, None]:
        for e in self.envs:
            yield from iter(e)

    def transform_matching(
        self,
        predicate: Callable[[ToxEnv], bool],
        mapper: Callable[[ToxEnv], Optional[ToxEnv]],
        max: Optional[int] = 1,
    ) -> "ToxEnvlist":
        """
        Takes two functions to pick an env and modify it; None means delete it
        from the envlist.  Returns a new envlist with the results.

        Can raise NoMatch if the predicate never matches.
        """
        new_envs: list[ToxEnv] = []
        it = iter(self.envs)
        done = 0
        for i in it:
            if predicate(i):
                new = mapper(i)
                if new is not None:
                    new_envs.append(new)
                done += 1
                if max is not None and done >= max:
                    break
            else:
                new_envs.append(i)

        if not done:
            raise NoMatch
        new_envs.extend(it)
        return self.__class__(tuple(new_envs))

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
        return "\n".join(str(x) for x in self.envs)
