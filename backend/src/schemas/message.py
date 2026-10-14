from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.pagination import PaginationParams


class MessageItem(BaseModel):
    message_id: int
    grouped_id: int | None = None
    posted_at: datetime
    channel_name: str
    text: str | None = None
    tg_link: str
    classifications: dict[str, list[str]] = {}
    created_at: datetime
    reply_to_msg_id: int | None = None
    is_has_replies: bool = False
    is_reply: bool = False


class MessagePaginationSearchParams(PaginationParams):
    channel: str = Field(default="baraholka_dubai", max_length=100)
    search: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)
    date_from: datetime | None = None
    date_to: datetime | None = None
