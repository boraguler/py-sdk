from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

Service = Literal["gamma", "data"]
Method = Literal["GET"]

QueryParamValue = str | int | float | bool

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RequestSpec(Generic[T]):
    service: Service
    method: Method
    path: str
    parse: Callable[[object], T]
    params: Mapping[str, QueryParamValue | None] | None = None


@dataclass(frozen=True, slots=True)
class OffsetPaginatedSpec(Generic[T]):
    service: Service
    path: str
    parse_items: Callable[[object], tuple[T, ...]]
    base_params: Mapping[str, QueryParamValue] | None = None


__all__ = [
    "Method",
    "OffsetPaginatedSpec",
    "QueryParamValue",
    "RequestSpec",
    "Service",
]
