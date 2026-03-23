from __future__ import annotations

import re
from typing import cast, Generator, Sequence, TypeVar

T = TypeVar("T")


def marklast(seq: Sequence[T]) -> Generator[tuple[T, bool], None, None]:
    last_idx = len(seq) - 1
    for i, x in enumerate(seq):
        yield x, i == last_idx


def common_prefix(a: str, b: str) -> str:
    buf = ""
    for c1, c2 in zip(a, b):
        if c1 != c2:
            break
        buf += c1
    return buf


def pre_num_suf(s: str) -> tuple[str, str, str] | None:
    parts_match = re.fullmatch(r"([a-zA-Z_]*)([0-9]+)([a-zA-Z_]*)", s)
    if not parts_match:
        return None
    return cast(tuple[str, str, str], parts_match.groups())
