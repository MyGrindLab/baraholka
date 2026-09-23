from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pycommontools.configs.logging import setup_logger

from src.infrastructure.mongo import MongoDBRepository
from src.schemas.message import (
    MessageItem,
    MessagePaginationSearchParams,
)
from src.schemas.pagination import PaginatedResponse
from src.services.channels import ChannelService
from src.services.messages import check_replies, get_all_replies_recursive

logger = setup_logger("api.messages")


router = APIRouter()


@router.get("/items", response_model=PaginatedResponse)
async def get_items(
    params: Annotated[MessagePaginationSearchParams, Query()],
) -> PaginatedResponse:
    repository = MongoDBRepository()

    query: dict = {
        "is_reply": {"$ne": True},
        "classifications": {"$exists": True, "$ne": {}},
    }

    if params.category and params.subcategory:
        query[f"classifications.{params.category}"] = {
            "$regex": params.subcategory,
            "$options": "i",
        }
    elif params.category:
        query[f"classifications.{params.category}"] = {"$exists": True}

    if params.search:
        query["text"] = {"$regex": params.search, "$options": "i"}

    if params.date_from or params.date_to:
        date_query = {}

        if params.date_from:
            date_query["$gte"] = params.date_from
        if params.date_to:
            date_query["$lte"] = params.date_to

        query["posted_at"] = date_query

    collection_name = params.channel if params.channel else "all"

    if collection_name == "all":
        channel_service = ChannelService()
        channels = await channel_service.get_all_channels()

        first_channel = channels[0]["name"]

        pipeline = [
            {"$match": query},
            {"$addFields": {"_channel": first_channel}},
        ]

        for channel in channels[1:]:
            pipeline.append(
                {
                    "$unionWith": {
                        "coll": channel["name"],
                        "pipeline": [
                            {"$match": query},
                            {"$addFields": {"_channel": channel["name"]}},
                        ],
                    }
                }
            )

        pipeline.extend(
            [
                {"$sort": {"posted_at": -1}},
                {
                    "$facet": {
                        "items": [
                            {"$skip": (params.page - 1) * params.page_size},
                            {"$limit": params.page_size},
                        ],
                        "total": [
                            {"$count": "count"},
                        ],
                    }
                },
            ]
        )

        cursor = repository.db[first_channel].aggregate(pipeline)
        result = await cursor.to_list(length=1)

        items = result[0]["items"]
        total = result[0]["total"][0]["count"] if result[0]["total"] else 0

        for item in items:
            item["is_has_replies"] = await check_replies(
                repository.db[item["_channel"]], item["message_id"]
            )
    else:
        collection = repository.db[collection_name]

        total = await collection.count_documents(query)

        skip = (params.page - 1) * params.page_size

        cursor = (
            collection.find(query)
            .sort("posted_at", -1)
            .skip(skip)
            .limit(params.page_size)
        )
        items = await cursor.to_list(length=params.page_size)

        for item in items:
            item["is_has_replies"] = await check_replies(collection, item["message_id"])

    message_items = [MessageItem(**item) for item in items]

    total_pages = (total + params.page_size - 1) // params.page_size

    return PaginatedResponse(
        items=message_items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


@router.get("/{channel}/{message_id}", response_model=MessageItem)
async def get_item_by_id(channel: str, message_id: int) -> MessageItem:
    repository = MongoDBRepository()

    item = await repository.db[channel].find_one(
        {
            "message_id": message_id,
            "is_reply": {"$ne": True},
            "classifications": {"$exists": True, "$ne": {}},
        }
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Item with message_id {message_id} in channel {channel} not found",
        )

    return MessageItem(**item)


@router.get("/{channel}/{message_id}/replies")
async def get_message_replies(channel: str, message_id: int) -> list[MessageItem]:
    repository = MongoDBRepository()

    parent = await repository.db[channel].find_one({"message_id": message_id})

    if not parent:
        raise HTTPException(
            status_code=404,
            detail=f"Message {message_id} not found in channel {channel}",
        )

    replies = await get_all_replies_recursive(repository.db[channel], message_id)

    return [MessageItem(**reply) for reply in replies]
