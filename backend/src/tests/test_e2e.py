import asyncio
import base64
import io

from PIL import Image
from pycommontools.configs.logging import setup_logger
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.core.settings import settings
from src.services.chatgpt import classify_ad

logger = setup_logger("test_classification", level="INFO")


def compress_and_resize_image(
    image_bytes: bytes, max_size: int = 800, quality: int = 50
) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()


async def test_messages_classification(
    channel_name: str, start_id: int, end_id: int
) -> None:
    if not settings.session_string:
        raise ValueError(
            "Session string is not configured. "
            "Please run 'python src/init_session.py' to generate one."
        )

    client = TelegramClient(
        StringSession(settings.session_string),
        settings.api_id,
        settings.api_hash,
        timeout=30,
        connection_retries=3,
        retry_delay=1,
    )

    try:
        await client.connect()

        if not await client.is_user_authorized():
            raise RuntimeError(
                "Session is not authorized. "
                "Please run 'python src/init_session.py' again."
            )

        channel_entity = await client.get_entity(channel_name)
        logger.info(f"Connected to channel: {channel_name}")

        total_input_tokens = 0
        total_output_tokens = 0

        for message_id in range(start_id, end_id + 1):
            try:
                message = await client.get_messages(channel_entity, ids=message_id)

                if not message:
                    logger.warning(f"Message {message_id} not found")
                    continue

                text = message.text or ""
                media_list = []

                if message.media and not getattr(message.media, "video", False):
                    try:
                        buffer = io.BytesIO()
                        await client.download_media(message.media, file=buffer)
                        media_bytes = buffer.getvalue()

                        if media_bytes:
                            compressed_image_bytes = compress_and_resize_image(
                                media_bytes
                            )
                            base64_image = base64.b64encode(
                                compressed_image_bytes
                            ).decode("utf-8")
                            media_list.append(f"data:image/jpeg;base64,{base64_image}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to download media for message {message_id}: {e}"
                        )

                logger.info(f"\n{'=' * 80}")
                logger.info(f"Message ID: {message_id}")
                logger.info(f"Text: {text[:200]}{'...' if len(text) > 200 else ''}")
                logger.info(f"Media count: {len(media_list)}")
                logger.info(f"Date: {message.date}")

                classifications, input_tokens, output_tokens = await classify_ad(
                    text, media_list
                )

                total_input_tokens += input_tokens
                total_output_tokens += output_tokens

                logger.info(f"Classifications: {classifications}")
                logger.info(
                    f"Tokens used: {input_tokens} input, {output_tokens} output"
                )

            except Exception as e:
                logger.error(f"Error processing message {message_id}: {e}")

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Total input tokens: {total_input_tokens}")
        logger.info(f"Total output tokens: {total_output_tokens}")

    finally:
        if client and client.is_connected():
            client.disconnect()
        logger.info("Disconnected from Telegram")


async def main() -> None:
    await test_messages_classification("dubai_barakholka", 144079, 144080)


if __name__ == "__main__":
    asyncio.run(main())
