from fastapi import Request, Response
from fastapi.routing import APIRouter
from pycommontools.configs.logging import setup_logger
from telegram import Update

from src.tg.bot import SubscriptionBot

logger = setup_logger("api.tg")

router = APIRouter()


@router.post("/telegram-webhook")
async def telegram_webhook(request: Request) -> Response:
    bot = SubscriptionBot()

    if not bot or not bot.application:
        logger.error("Bot instance or application not initialized")
        return Response(status_code=500)

    json_data = await request.json()

    update = Update.de_json(json_data, bot.application.bot)

    await bot.application.process_update(update)

    return Response(status_code=200)
