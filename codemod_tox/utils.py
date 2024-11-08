from typing import Generator, Sequence, TypeVar

T = TypeVar("T")


def _marklast(seq: Sequence[T]) -> Generator[tuple[T, bool], None, None]:
    last_idx = len(seq) - 1
    for i, x in enumerate(seq):
        yield x, i == last_idx


def _common_prefix(a: str, b: str) -> str:
    buf = ""
    for c1, c2 in zip(a, b):
        if c1 != c2:
            break
        buf += c1
    return buf
