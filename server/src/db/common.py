from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar("T")


class PaginationMeta(BaseModel):
    current_page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1)
    total_items: int = Field(..., ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: PaginationMeta


class SingleResponse(BaseModel, Generic[T]):
    data: T
