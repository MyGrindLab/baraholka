from pydantic import BaseModel, Field


class ChannelItem(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
