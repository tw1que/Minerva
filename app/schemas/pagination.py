from __future__ import annotations

from typing import Generic, TypeVar

from pydantic.generics import GenericModel


T = TypeVar("T")


class Page(GenericModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
