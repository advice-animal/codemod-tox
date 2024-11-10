from __future__ import annotations

from typing import Generator

from .utils import _common_prefix


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
