from pycommontools.configs.logging import setup_logger

from src.infrastructure.mongo import MongoDBRepository

logger = setup_logger("channels")


class ChannelService:
    def __init__(self) -> None:
        self.repository = MongoDBRepository()
        self.collection = self.repository.db["channels"]

    async def get_all_channels(self) -> list[dict]:
        cursor = self.collection.find({})
        channels = await cursor.to_list(length=None)

        for channel in channels:
            channel["_id"] = str(channel["_id"])

        return channels

    async def get_channel_by_name(self, name: str) -> dict | None:
        channel = await self.collection.find_one({"name": name})

        if channel:
            channel["_id"] = str(channel["_id"])

        return channel
