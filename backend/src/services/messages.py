from motor.motor_asyncio import AsyncIOMotorCollection


async def check_replies(collection: AsyncIOMotorCollection, message_id: int) -> bool:
    direct_replies_cursor = collection.find(
        {"reply_to_msg_id": message_id, "is_reply": True}
    ).sort("posted_at", 1)

    direct_replies = await direct_replies_cursor.to_list(length=None)

    return bool(direct_replies)


async def get_all_replies_recursive(
    collection: AsyncIOMotorCollection,
    message_id: int,
    collected_ids: set[int] | None = None,
) -> list[dict]:
    if collected_ids is None:
        collected_ids = set()

    if message_id in collected_ids:
        return []

    collected_ids.add(message_id)

    direct_replies_cursor = collection.find(
        {"reply_to_msg_id": message_id, "is_reply": True}
    ).sort("posted_at", 1)

    direct_replies = await direct_replies_cursor.to_list(length=None)

    all_replies = list(direct_replies)

    for reply in direct_replies:
        nested_replies = await get_all_replies_recursive(
            collection, reply["message_id"], collected_ids
        )
        all_replies.extend(nested_replies)

    return all_replies
