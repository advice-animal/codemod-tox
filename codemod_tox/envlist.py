from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generator, Optional

from .base import ToxBase
from .env import ToxEnv
from .exceptions import NoFactorMatch, NoMatch
from .options import ToxOptions
from .parse import TOX_ENV_TOKEN_RE


@dataclass(frozen=True)
class ToxEnvlist(ToxBase):
    """
    An envlist.

    e.g. `py{37,38}-tests, coverage, lint`

    Both comma and newline separated are supported during parsing, and the
    style is preserved in `str()`: a one-line comma-separated input stays
    comma-separated; a multi-line input uses newlines, with a leading newline.
    Check that set(a) != set(b) before changing a configuration value to
    avoid (one-time) churn.
    """

    envs: tuple[ToxEnv, ...]
    separator: str = "\n"
    leading_newline: bool = False

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
        return self.__class__(tuple(new_envs), self.separator, self.leading_newline)

    @classmethod
    def parse(cls, s: str) -> "ToxEnvlist":
        pieces = []
        buf = ""
        has_newline = False
        comma_sep = None

        for match in TOX_ENV_TOKEN_RE.finditer(s):
            # This will double-parse but these strings are typically pretty
            # trivial and we've restricted the character set significantly so
            # this should be roughly linear
            if match.group("comma"):
                if comma_sep is None:
                    comma_sep = match.group("comma")
                assert buf
                pieces.append(ToxEnv.parse(buf))
                buf = ""
            elif match.group("newline"):
                has_newline = True
                if buf:
                    pieces.append(ToxEnv.parse(buf))
                    buf = ""
            elif match.group("space"):
                pass
            else:
                buf += match.group(0)

        if buf:
            pieces.append(ToxEnv.parse(buf))

        if not has_newline and comma_sep is not None:
            separator = comma_sep
            leading_newline = False
        else:
            separator = "\n"
            leading_newline = has_newline

        return cls(tuple(pieces), separator=separator, leading_newline=leading_newline)

    def add_numeric_option(self, value: str) -> "ToxEnvlist":
        new_envs: list[ToxEnv] = []
        added = False
        for env in self.envs:
            if not any(isinstance(p, ToxOptions) for p in env.pieces):
                new_envs.append(env)
                continue
            try:
                new_envs.append(env.add_numeric_option(value))
                added = True
            except NoFactorMatch:
                new_envs.append(env)
        if not added:
            new_envs.append(ToxEnv.parse(value))
        return self.__class__(tuple(new_envs), self.separator, self.leading_newline)

    def __str__(self) -> str:
        if not self.envs:
            return ""
        result = self.separator.join(str(x) for x in self.envs)
        return ("\n" if self.leading_newline else "") + result
