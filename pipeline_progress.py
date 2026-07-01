from __future__ import annotations

from typing import Generic, Iterable, Iterator, TypeVar

try:
    from tqdm.auto import tqdm
except ImportError:  # pragma: no cover - exercised only in minimal runtime environments
    tqdm = None

_T = TypeVar("_T")


class _NoOpProgress(Generic[_T]):
    def __init__(self, iterable: Iterable[_T] | None = None, **_: object) -> None:
        self._iterable = iterable

    def __iter__(self) -> Iterator[_T]:
        return iter(self._iterable if self._iterable is not None else ())

    def __enter__(self) -> "_NoOpProgress[_T]":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def update(self, _: int = 1) -> None:
        return None

    def set_postfix(self, **_: object) -> None:
        return None


def progress_bar(iterable: Iterable[_T] | None = None, **kwargs: object):
    if tqdm is None:
        return _NoOpProgress(iterable, **kwargs)
    return tqdm(iterable, **kwargs)
