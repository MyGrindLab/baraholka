from fastapi import APIRouter, HTTPException

from src.schemas.channels import ChannelItem
from src.services.channels import ChannelService

router = APIRouter()


@router.get("/channels")
async def get_channels() -> list[ChannelItem]:
    service = ChannelService()
    channels = await service.get_all_channels()

    return [ChannelItem(**channel) for channel in channels]


@router.get("/channels/{name}")
async def get_channel(name: str) -> ChannelItem:
    service = ChannelService()
    channel = await service.get_channel_by_name(name)

    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel '{name}' not found")

    return ChannelItem(**channel)
