import asyncio
import sys

from pycommontools.configs.logging import setup_logger
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.core.settings import settings

logger = setup_logger("init_session")


async def init_session():
    logger.info("=== Telethon Session Initialization ===")
    logger.info("")
    logger.info("This script will help you create a session string for Telethon.")
    logger.info("You will need to:")
    logger.info("  1. Enter your phone number")
    logger.info("  2. Enter the code sent to your Telegram")
    logger.info("  3. Optionally enter 2FA password if enabled")
    logger.info("")

    client = TelegramClient(
        StringSession(),
        settings.api_id,
        settings.api_hash,
    )

    try:
        await client.connect()

        logger.info("Connecting to Telegram...")

        if not await client.is_user_authorized():
            logger.info("")
            logger.info("You are not authorized. Starting authorization process...")

            phone = input(
                f"Enter your phone number (default: {settings.phone_number}): "
            ).strip()

            if not phone:
                phone = settings.phone_number

            await client.send_code_request(phone)
            logger.info(f"Code sent to {phone}")

            code = input("Enter the code you received: ").strip()

            try:
                await client.sign_in(phone, code)
            except Exception as e:
                if "password" in str(e).lower() or "2fa" in str(e).lower():
                    password = input("Enter your 2FA password: ").strip()
                    await client.sign_in(password=password)
                else:
                    raise

        if await client.is_user_authorized():
            logger.info("")
            logger.info("✓ Successfully authorized!")

            me = await client.get_me()

            logger.info(f"Logged in as: {me.first_name} (@{me.username})")  # type:ignore

            session_string = client.session.save()  # type:ignore

            logger.info("")
            logger.info("=" * 60)
            logger.info("SESSION STRING GENERATED")
            logger.info("=" * 60)
            logger.info("")
            logger.info(
                "Copy the following session string and add it to your .env file:"
            )
            logger.info("")
            logger.info(f"SESSION_STRING={session_string}")
            logger.info("")
            logger.info("=" * 60)
            logger.info("")
            logger.info("⚠️  IMPORTANT:")
            logger.info("  - Keep this session string SECRET")
            logger.info("  - Do NOT share it with anyone")
            logger.info("  - Do NOT commit it to git")
            logger.info("  - Add it to .env file only")
            logger.info("")

            return session_string
        else:
            logger.error("Authorization failed")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during initialization: {e}", exc_info=True)
        sys.exit(1)
    finally:
        client.disconnect()


async def verify_session(session_string: str):
    """Проверяет, что session string работает корректно."""

    logger.info("")
    logger.info("Verifying session string...")

    client = TelegramClient(
        StringSession(session_string),
        settings.api_id,
        settings.api_hash,
    )

    try:
        await client.connect()

        if await client.is_user_authorized():
            me = await client.get_me()
            logger.info(f"✓ Session is valid for: {me.first_name} (@{me.username})")  # type:ignore
            return True
        else:
            logger.error("✗ Session is not authorized")
            return False

    except Exception as e:
        logger.error(f"✗ Error verifying session: {e}")
        return False
    finally:
        client.disconnect()


async def main():
    """Главная функция."""

    # Проверяем, есть ли уже session string
    if settings.session_string:
        logger.info("Found existing SESSION_STRING in configuration")

        verify = input("Do you want to verify it? (yes/no): ").strip().lower()
        if verify in ["yes", "y"]:
            is_valid = await verify_session(settings.session_string)
            if is_valid:
                logger.info("")
                logger.info("✓ Your session is valid and ready to use!")
                return
            else:
                logger.info("")
                logger.info("✗ Your session is invalid. Generating a new one...")
        else:
            regenerate = (
                input("Do you want to generate a new session? (yes/no): ")
                .strip()
                .lower()
            )
            if regenerate not in ["yes", "y"]:
                logger.info("Exiting...")
                return

    # Генерируем новую сессию
    session_string = await init_session()

    # Проверяем её
    if session_string:
        await verify_session(session_string)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nExiting...")
        sys.exit(0)
