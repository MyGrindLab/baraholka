from datetime import datetime

from pydantic import BaseModel

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
    channel: str = "baraholka_dubai"
    search: str | None = None
    category: str | None = None
    subcategory: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
