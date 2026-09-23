import asyncio

from pycommontools.configs.logging import setup_logger

from src.infrastructure.mongo import MongoDBManager

logger = setup_logger("add_channel")

CHANNELS_LIST = [
    "baraholka_dubai",
    "dubaibaraholka",
    "dubai_barakholka",
    "dxbbaraholka",
    "T2TDubaiChat",
]


async def add_channel():
    mongo_manager = MongoDBManager()
    await mongo_manager.connect()

    for channel_name in CHANNELS_LIST:
        result = await mongo_manager.db.channels.update_one(
            {"name": channel_name},
            {"$set": {"name": channel_name}},
            upsert=True,
        )
        if result.upserted_id:
            logger.info(f"Канал '{channel_name}' добавлен с ID: {result.upserted_id}")

    await mongo_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(add_channel())
