from __future__ import annotations

from typing import Callable, Generator, TypeVar

from .utils import common_prefix

T = TypeVar("T")


class ToxBase:
    def __iter__(self) -> Generator[str, None, None]:  # pragma: no cover
        raise NotImplementedError

    def map(self, func: Callable[[str], T]) -> Generator[T, None, None]:
        for x in self:
            yield func(x)

    def map_all(self, func: Callable[[str], bool]) -> bool:
        """Wrapper around all(map(...))"""
        return all(self.map(func))

    def map_any(self, func: Callable[[str], bool]) -> bool:
        """Wrapper around any(map(...))"""
        return any(self.map(func))

    def startswith(self, prefix: str) -> bool:
        """
        Returns whether all possibilities start with `prefix`.
        """
        return self.map_all(lambda x: x.startswith(prefix))

    def endswith(self, suffix: str) -> bool:
        """
        Returns whether all possibilities end with `suffix`.
        """
        return self.map_all(lambda x: x.endswith(suffix))

    def only(self, value: str) -> bool:
        """
        Returns whether all possibilities are exactly `value`.
        """
        return self.map_all(value.__eq__)

    def one(self) -> str:
        """
        Returns the string if only one string matches, otherwise raise ValueError.
        """
        s = set(self)
        if len(s) == 1:
            return next(iter(s))
        raise ValueError(f"Multiple matches: {s}")

    def fold(self, func: Callable[[str, str], str]) -> str:
        """Like reduce"""
        prev = None
        for item in self:
            if prev is None:
                prev = item
            else:
                prev = func(prev, item)
        assert prev is not None
        return prev

    def common_prefix(self) -> str:
        """Returns the string that is common prefix."""
        return self.fold(common_prefix)

    def __bool__(self) -> bool:
        """Returns whether any of the possibilities are truthy"""
        return self.map_any(lambda x: bool(x))

    @classmethod
    def parse(cls, s: str) -> "ToxBase":  # pragma: no cover
        raise NotImplementedError

    def __str__(self) -> str:  # pragma: no cover
        raise NotImplementedError
