from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

from .base import ToxBase
from .env import ToxEnv
from .parse import TOX_ENV_TOKEN_RE
from .utils import _marklast


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
