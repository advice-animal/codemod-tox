from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .base import ToxBase
from .env import ToxEnv
from .parse import TOX_CONDITIONAL_RE


@dataclass(frozen=True)
class ToxConditional(ToxBase):
    lines: tuple[tuple[Optional[ToxEnv], str], ...]

    def evaluate(self, env: str) -> str:
        buf: list[str] = []
        for i, j in self.lines:
            if isinstance(i, ToxEnv):
                if i.matches(env):
                    buf.append(j)
            else:
                buf.append(j)
        return "\n".join(buf)

    @classmethod
    def parse(cls, value: str) -> "ToxConditional":
        lines: list[tuple[Optional[ToxEnv], str]] = []
        for line in value.splitlines():
            print(repr(line))
            match = TOX_CONDITIONAL_RE.fullmatch(line)
            if match:
                lines.append(
                    (ToxEnv.parse(match.group("condition")), match.group("line"))
                )
            else:
                lines.append((None, line))

        return cls(tuple(lines))

    def __str__(self) -> str:
        return "\n".join(
            "%s: %s" % (i, j) if i is not None else j for i, j in self.lines
        )
