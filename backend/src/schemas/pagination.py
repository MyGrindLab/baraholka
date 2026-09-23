from pydantic import BaseModel


class PaginatedResponse[T: BaseModel](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10
