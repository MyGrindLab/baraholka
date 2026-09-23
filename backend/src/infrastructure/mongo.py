from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pycommontools.configs.logging import setup_logger
from pycommontools.resources.singleton import Singleton

from src.core.settings import settings

logger = setup_logger("mongo")


def normalize_keyword(keyword: str) -> str:
    """
    Normalize keyword by removing common Russian endings for better matching.
    Keeps only the stem of the word.
    """
    keyword = keyword.lower().strip()

    suffixes = [
        "ами",
        "ями",
        "ах",
        "ях",
        "ом",
        "ем",
        "ам",
        "ям",
        "ов",
        "ев",
        "ой",
        "ей",
        "ий",
        "ый",
        "ая",
        "яя",
        "ое",
        "ее",
        "ие",
        "ые",
        "ого",
        "его",
        "ому",
        "ему",
        "ым",
        "им",
        "ом",
        "ем",
        "у",
        "ю",
        "а",
        "я",
        "ы",
        "и",
        "е",
        "о",
    ]

    suffixes.sort(key=len, reverse=True)

    for suffix in suffixes:
        if len(keyword) > 4 and keyword.endswith(suffix):
            stem = keyword[: -len(suffix)]
            if len(stem) >= 3:
                return stem

    return keyword


class MongoDBManager(metaclass=Singleton):
    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        self._client = AsyncIOMotorClient(settings.mongo_url)
        self._db = self._client[settings.mongo_db_name]

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("Database not initialized")

        return self._db

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()


def get_mongo_db() -> AsyncIOMotorDatabase:
    mongo_manager = MongoDBManager()

    return mongo_manager.db


class MongoDBRepository:
    def __init__(self, db: AsyncIOMotorDatabase | None = None) -> None:
        if db is None:
            db = get_mongo_db()

        self.db: AsyncIOMotorDatabase = db
        self.client = self.db.client if self.db is not None else None

    async def get_last_message_id(self, channel: str) -> int | None:
        result = await self.db[channel].find_one(sort=[("message_id", -1)])

        if result and "message_id" in result:
            return result["message_id"]

        return None

    async def get_last_datetime(self, channel: str) -> datetime:
        result = await self.db[channel].find_one(sort=[("posted_at", -1)])

        if result and "posted_at" in result:
            return result["posted_at"]

        return datetime.now(UTC) - timedelta(days=7)

    async def save_messages(self, channel: str, items: list[dict]) -> int:
        out_ = 0

        for item in items:
            item["created_at"] = datetime.now(UTC)

            await self.db[channel].update_one(
                {"message_id": item["message_id"]}, {"$set": item}, upsert=True
            )

            out_ += 1

        return out_

    async def ensure_user(self, user_id: int, username: str) -> dict:
        result = await self.db.users.find_one_and_update(
            {"user_id": user_id},
            {
                "$set": {
                    "username": username,
                    "last_active": datetime.now(UTC),
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "subscriptions": {},
                    "keywords": [],
                    "channels": [],
                    "created_at": datetime.now(UTC),
                },
            },
            upsert=True,
            return_document=True,
        )
        return result

    async def get_user_subscriptions(self, user_id: int) -> dict:
        result = await self.db.users.find_one({"user_id": user_id})
        if result is None:
            return {"subscriptions": {}}
        return result

    async def toggle_subcategory_subscription(
        self, user_id: int, category: str, subcategory: str
    ):
        user = await self.get_user_subscriptions(user_id)
        subscriptions = user.get("subscriptions", {})

        category_subs = subscriptions.get(category, [])

        if subcategory in category_subs:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$pull": {f"subscriptions.{category}": subcategory}},
            )
            user = await self.get_user_subscriptions(user_id)
            if not user.get("subscriptions", {}).get(category):
                await self.db.users.update_one(
                    {"user_id": user_id}, {"$unset": {f"subscriptions.{category}": ""}}
                )
        else:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$addToSet": {f"subscriptions.{category}": subcategory}},
            )

    async def remove_subcategory_subscription(
        self, user_id: int, category: str, subcategory: str
    ):
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$pull": {f"subscriptions.{category}": subcategory}},
        )
        user = await self.get_user_subscriptions(user_id)
        if not user.get("subscriptions", {}).get(category):
            await self.db.users.update_one(
                {"user_id": user_id}, {"$unset": {f"subscriptions.{category}": ""}}
            )

    async def get_subscribers_for_item(
        self, category: str, subcategory: str, channel_name: str = ""
    ) -> list[dict]:
        query: dict = {f"subscriptions.{category}": subcategory}

        if channel_name:
            query["$or"] = [
                {"channels": {"$size": 0}},
                {"channels": {"$exists": False}},
                {"channels": channel_name},
            ]

        cursor = self.db.users.find(query)
        subscribers = await cursor.to_list(length=None)
        return subscribers

    async def add_keyword(self, user_id: int, keyword: str) -> None:
        """Add a keyword to user's keyword subscriptions."""
        # Normalize keyword to lowercase for case-insensitive matching
        keyword = keyword.lower().strip()
        await self.db.users.update_one(
            {"user_id": user_id}, {"$addToSet": {"keywords": keyword}}
        )

    async def remove_keyword(self, user_id: int, keyword: str) -> None:
        """Remove a keyword from user's keyword subscriptions."""
        keyword = keyword.lower().strip()
        await self.db.users.update_one(
            {"user_id": user_id}, {"$pull": {"keywords": keyword}}
        )

    async def get_user_keywords(self, user_id: int) -> list[str]:
        """Get all keywords for a user."""
        user = await self.db.users.find_one({"user_id": user_id})
        if user:
            return user.get("keywords", [])
        return []

    async def get_subscribers_by_keyword(self, keyword: str) -> list[dict]:
        """Get all users subscribed to a specific keyword."""
        # Case-insensitive search
        keyword = keyword.lower().strip()
        cursor = self.db.users.find({"keywords": keyword})
        subscribers = await cursor.to_list(length=None)
        return subscribers

    async def get_all_keyword_subscribers(self) -> list[dict]:
        """Get all users who have at least one keyword subscription."""
        cursor = self.db.users.find({"keywords": {"$exists": True, "$ne": []}})
        subscribers = await cursor.to_list(length=None)
        return subscribers

    async def toggle_channel(self, user_id: int, channel_name: str) -> None:
        """Toggle channel subscription for a user."""
        user = await self.db.users.find_one({"user_id": user_id})
        if not user:
            return

        channels = user.get("channels", [])

        if channel_name in channels:
            await self.db.users.update_one(
                {"user_id": user_id}, {"$pull": {"channels": channel_name}}
            )
        else:
            await self.db.users.update_one(
                {"user_id": user_id}, {"$addToSet": {"channels": channel_name}}
            )

    async def get_user_channels(self, user_id: int) -> list[str]:
        """Get all channels for a user."""
        user = await self.db.users.find_one({"user_id": user_id})
        if user:
            return user.get("channels", [])
        return []

    async def set_all_channels(self, user_id: int, channels: list[str]) -> None:
        """Set all channels for a user."""
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"channels": channels}}
        )

    async def clear_all_channels(self, user_id: int) -> None:
        """Clear all channel subscriptions for a user."""
        await self.db.users.update_one({"user_id": user_id}, {"$set": {"channels": []}})
