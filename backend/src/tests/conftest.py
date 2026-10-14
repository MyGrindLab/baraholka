import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from src.infrastructure.mongo import MongoDBManager
from src.main import app

# Manual script that needs a live Telegram session; not a pytest module.
collect_ignore = ["test_e2e.py"]

BASE_TIME = datetime(2025, 1, 1, tzinfo=UTC)


def make_message(
    channel: str,
    message_id: int,
    text: str,
    classifications: dict[str, list[str]] | None = None,
    **extra: object,
) -> dict:
    return {
        "message_id": message_id,
        "posted_at": BASE_TIME + timedelta(minutes=message_id),
        "channel_name": channel,
        "text": text,
        "tg_link": f"https://t.me/{channel}/{message_id}",
        "created_at": BASE_TIME,
        "classifications": classifications or {"electronics": ["phones"]},
        **extra,
    }


@pytest.fixture
def db() -> Iterator:
    """In-memory Mongo installed into the MongoDBManager singleton."""
    manager = MongoDBManager()
    previous = manager._db
    mock_db = AsyncMongoMockClient()["test"]
    manager._db = mock_db
    try:
        yield mock_db
    finally:
        manager._db = previous


@pytest.fixture
def seeded_db(db):
    """Seeds channels chan_a and chan_b plus message documents."""

    async def seed() -> None:
        await db["channels"].insert_many([{"name": "chan_a"}, {"name": "chan_b"}])
        await db["chan_a"].insert_many(
            [
                make_message("chan_a", 1, "a.b phone"),
                make_message("chan_a", 2, "axb phone"),
                make_message("chan_a", 3, "sofa", {"furniture": ["sofas", "tables"]}),
                make_message("chan_a", 4, "reply", reply_to_msg_id=1, is_reply=True),
            ]
        )
        await db["chan_b"].insert_many([make_message("chan_b", 10, "other")])

    asyncio.run(seed())
    return db


@pytest.fixture
def client(seeded_db) -> TestClient:
    # No `with`: lifespan (Mongo connect, scheduler, bot) must not run.
    return TestClient(app)
