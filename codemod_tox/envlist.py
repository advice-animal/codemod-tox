from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Generator, Optional

from .base import ToxBase
from .env import ToxEnv
from .exceptions import NoFactorMatch, NoMatch
from .options import ToxOptions
from .parse import TOX_ENV_TOKEN_RE
from .utils import pre_num_suf


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

        if has_newline:
            separator = "\n"
            leading_newline = True
        else:
            separator = comma_sep if comma_sep is not None else ","
            leading_newline = False

        return cls(tuple(pieces), separator=separator, leading_newline=leading_newline)

    @staticmethod
    def _after_numeric(envs: list[ToxEnv], value: str) -> int:
        """
        Index after the last env that looks like `value`: the same alphabetic
        prefix followed by a digit.  The end of the list if none do.
        """
        if (pns := pre_num_suf(value)) is None:
            return len(envs)
        numeric = re.compile(re.escape(pns[0]) + r"\d")
        for i in range(len(envs) - 1, -1, -1):
            if any(numeric.match(name) for name in envs[i]):
                return i + 1
        return len(envs)

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
            new_envs.insert(self._after_numeric(new_envs, value), ToxEnv.parse(value))
        return self.__class__(tuple(new_envs), self.separator, self.leading_newline)

    def __str__(self) -> str:
        if not self.envs:
            return ""
        result = self.separator.join(str(x) for x in self.envs)
        return ("\n" if self.leading_newline else "") + result
