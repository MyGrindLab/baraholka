import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pycommontools.configs.logging import setup_logger

from src.api.categories import router as categories_router
from src.api.channels import router as channels_router
from src.api.health import router as health_router
from src.api.messages import router as messages_router
from src.api.tg import router as tg_router
from src.core.settings import settings
from src.infrastructure.mongo import MongoDBManager
from src.services.monitor import run_scheduler
from src.tg.bot import SubscriptionBot

logger = setup_logger("main", level=settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    mongo_manager = MongoDBManager()

    await mongo_manager.connect()
    logger.info("API started and connected to MongoDB")

    await mongo_manager.db.command("ping")

    scheduler_task = asyncio.create_task(run_scheduler())
    logger.info("Scheduler started in background")

    bot = SubscriptionBot()

    logger.info("Starting bot in webhook mode...")
    await bot.setup()

    yield

    scheduler_task.cancel()

    if bot:
        await bot.shutdown()

    tasks = [scheduler_task]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass

    logger.info("Background tasks stopped")

    await mongo_manager.disconnect()
    logger.info("API shutdown and disconnected from MongoDB")


app = FastAPI(
    title="Baraholka API",
    description="API for accessing Baraholka channel messages",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(messages_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(channels_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(tg_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allow_origins] if settings.debug else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
