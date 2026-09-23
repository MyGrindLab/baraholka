import asyncio
import base64
import io
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from PIL import Image
from pycommontools.configs.logging import setup_logger
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel, User

from src.core.settings import settings
from src.infrastructure.mongo import MongoDBRepository
from src.services.channels import ChannelService
from src.services.chatgpt import classify_ad
from src.services.notifications import NotificationService

logger = setup_logger("monitor")


class ChannelMonitor:
    def __init__(self) -> None:
        self.mongo = MongoDBRepository()
        self._telegram_client: TelegramClient | None = None
        # self._channels: list[str] = []

    async def start(self) -> None:
        if not settings.session_string:
            raise ValueError(
                "Session string is not configured. "
                "Please run 'python src/init_session.py' to generate one."
            )

        self._telegram_client = TelegramClient(
            StringSession(settings.session_string),
            settings.api_id,
            settings.api_hash,
            timeout=30,
            connection_retries=3,
            retry_delay=1,
        )

        try:
            await self._telegram_client.connect()

            channel_service = ChannelService()
            channels = await channel_service.get_all_channels()

            logger.info(f"Monitoring {len(channels)} active channels")

            tasks = [
                asyncio.create_task(self._process_channel(channel["name"]))
                for channel in channels
            ]

            # self._channels = [channel["name"] for channel in channels]

            await asyncio.gather(*tasks)
        finally:
            await self.disconnect()

    @property
    def telegram_client(self) -> TelegramClient:
        if self._telegram_client is None:
            raise RuntimeError("Telegram client is not initialized")

        return self._telegram_client

    @staticmethod
    def compress_and_resize_image(
        image_bytes: bytes, max_size: int = 800, quality: int = 50
    ) -> bytes:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail((max_size, max_size))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            return buffer.getvalue()

    async def group_messages_in_batches(
        self, messages: list, channel_name: str
    ) -> tuple[list[dict], list[dict]]:
        grouped = {}
        replies = []

        for message in messages:
            text = message.text or ""
            tg_link = f"https://t.me/c/{abs(message.peer_id.channel_id)}/{message.id}"

            is_reply = message.reply_to_msg_id is not None

            content = None
            document_media = getattr(message.media, "document", None)

            if (
                message.media
                and not getattr(message.media, "video", False)
                and not (
                    document_media
                    and document_media.mime_type
                    and document_media.mime_type.startswith("video/")
                )
            ):
                try:
                    buffer = io.BytesIO()
                    await self.telegram_client.download_media(
                        message.media, file=buffer
                    )
                    media_bytes = buffer.getvalue()

                    assert isinstance(
                        media_bytes, bytes
                    ), "Downloaded media is not in bytes format"

                    if media_bytes:
                        compressed_image_bytes = self.compress_and_resize_image(
                            media_bytes
                        )
                        base64_image = base64.b64encode(compressed_image_bytes).decode(
                            "utf-8"
                        )
                        content = f"data:image/jpeg;base64,{base64_image}"
                except Exception as e:
                    logger.exception(message)
                    logger.exception(
                        "%s: Failed to download or process media for message ID %s: %s",
                        channel_name,
                        message.id,
                        str(e),
                    )

            if is_reply:
                reply_item = {
                    "message_id": message.id,
                    "posted_at": message.date,
                    "text": text,
                    "tg_link": tg_link,
                    "reply_to_msg_id": message.reply_to_msg_id,
                    "is_reply": True,
                    "category": None,
                    "subcategory": None,
                    "channel_name": channel_name,
                }
                replies.append(reply_item)
                continue

            if message.grouped_id:
                if message.grouped_id not in grouped:
                    item = {
                        "grouped_id": message.grouped_id,
                        "message_id": message.id,
                        "posted_at": message.date,
                        "text": text,
                        "tg_link": tg_link,
                        "submessage_ids": [],
                        "media": [content] if content else [],
                        "reply_to_msg_id": None,
                        "is_reply": False,
                        "channel_name": channel_name,
                    }
                    grouped[message.grouped_id] = item
                else:
                    grouped[message.grouped_id]["submessage_ids"].append(message.id)

                    if content:
                        grouped[message.grouped_id]["media"].append(content)
            else:
                item = {
                    "grouped_id": message.grouped_id,
                    "message_id": message.id,
                    "posted_at": message.date,
                    "text": text,
                    "tg_link": tg_link,
                    "submessage_ids": [],
                    "media": [content] if content else [],
                    "reply_to_msg_id": None,
                    "is_reply": False,
                    "channel_name": channel_name,
                }
                grouped[message.id] = item

        return list(grouped.values()), replies

    async def _process_channel(self, channel_name: str) -> None:
        if not self._telegram_client:
            raise RuntimeError("Telegram client is not initialized")

        if not await self._telegram_client.is_user_authorized():
            raise RuntimeError(
                "Session is not authorized. "
                "Please run 'python src/init_session.py' again."
            )

        try:
            logger.info(f"Processing channel: {channel_name}")
            channel_entity = await self._telegram_client.get_entity(channel_name)

            await self._process_messages(channel_entity)
        except Exception as e:
            logger.exception("Error processing channel %s: %s", channel_name, str(e))

    async def _process_messages(self, channel_entity) -> None:
        last_message_id = await self.mongo.get_last_message_id(channel_entity.username)

        if last_message_id:
            batch_messages = await self._fetch_batch(
                channel_entity, last_message_id=last_message_id
            )
        else:
            last_datetime = await self.mongo.get_last_datetime(channel_entity.username)
            batch_messages = await self._fetch_batch(
                channel_entity, last_datetime=last_datetime
            )

        messages = await self._group_and_save_batch(
            channel_entity.username, batch_messages
        )

        try:
            notification_service = NotificationService()
            await notification_service.notify_new_items_batch(messages)
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")

    async def _fetch_batch(
        self,
        channel: Channel,
        last_message_id: int | None = None,
        last_datetime: datetime | None = None,
    ) -> list[dict]:
        params = {}
        if last_message_id:
            params["min_id"] = last_message_id
        elif last_datetime:
            last_datetime_unix = int(last_datetime.timestamp()) + 1
            params["offset_date"] = last_datetime_unix
        else:
            raise ValueError("Either last_message_id or last_datetime must be provided")

        batch_messages: list = []
        async for message in self.telegram_client.iter_messages(
            channel, **params, reverse=True
        ):
            if (
                len(batch_messages) >= settings.messages_batch_size
                and not message.grouped_id
            ):
                break

            sender = await message.get_sender()

            if isinstance(sender, User) and sender.bot:
                continue

            batch_messages.append(message)

        return batch_messages

    async def _group_and_save_batch(
        self, channel: str, batch_messages: list
    ) -> list[dict]:
        if not batch_messages:
            return []

        total_input_tokens = 0
        total_output_tokens = 0

        messages, replies = await self.group_messages_in_batches(
            batch_messages, channel
        )

        messages_to_process = []
        for message in messages:
            if not message["grouped_id"]:
                messages_to_process.append(message)

            existed_msg = await self.mongo.db[channel].find_one(
                filter={"grouped_id": message["grouped_id"]}
            )

            if not existed_msg:
                messages_to_process.append(message)

            # TODO: add duplicate detection logic here
            # message_hash = hash(
            # f"{message['text']}{message['media']}{message['user']}"
            # )

        logger.info(
            f"{channel}: New {len(messages)} messages and {len(replies)} replies"
        )

        for item in messages_to_process:
            classifications, input_tokens, output_tokens = await classify_ad(
                item["text"], item.get("media", [])
            )

            item["classifications"] = classifications
            item.pop("media", None)

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            await asyncio.sleep(0.1)  # To avoid hitting rate limits

        logger.info(f"Total prompt tokens: {total_input_tokens}")
        logger.info(f"Total completion tokens: {total_output_tokens}")

        all_items = messages_to_process + replies
        await self.mongo.save_messages(channel, all_items)

        return messages_to_process

    async def disconnect(self) -> None:
        try:
            self.telegram_client.disconnect()
        except Exception as e:
            logger.warning("Error disconnecting Telegram client: %s", e)


async def run_monitoring() -> None:
    logger.info("Starting monitoring...")

    try:
        monitor = ChannelMonitor()
        await monitor.start()
    except Exception as e:
        logger.exception("Error in run_monitoring: %s", e)
        raise


async def run_monitoring_with_timeout() -> None:
    try:
        await asyncio.wait_for(run_monitoring(), timeout=300)
    except TimeoutError:
        logger.error("Monitoring task exceeded 5 minute timeout and was cancelled")


async def run_scheduler() -> None:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        run_monitoring_with_timeout,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        max_instances=1,
    )

    scheduler.start()

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down...")
    finally:
        scheduler.shutdown()
