import asyncio

from pycommontools.configs.logging import setup_logger
from pycommontools.resources.singleton import Singleton
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from src.core.settings import settings
from src.infrastructure.mongo import MongoDBRepository

logger = setup_logger("notifications")


class NotificationService(metaclass=Singleton):
    def __init__(self) -> None:
        self.bot = Bot(token=settings.telegram_bot_token)
        self.mongo = MongoDBRepository()

    async def send_notification(
        self,
        user_id: int,
        message_text: str,
        parse_mode: str = "HTML",
        link_preview: bool = True,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> bool:
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=parse_mode,
                disable_web_page_preview=not link_preview,
                reply_markup=reply_markup,
            )
            logger.debug(f"Notification sent to user {user_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
            return False

    async def notify_new_item(self, item: dict) -> None:
        classifications = item.get("classifications", {})
        link = item.get("tg_link", "")
        channel_name = item.get("channel_name", "")

        if not classifications:
            return

        all_subscribers = set()
        notification_pairs = []

        for category, subcategories in classifications.items():
            if not isinstance(subcategories, list):
                continue

            for subcategory in subcategories:
                subscribers = await self.mongo.get_subscribers_for_item(
                    category, subcategory, channel_name
                )

                for subscriber in subscribers:
                    user_id = subscriber.get("user_id")
                    if user_id:
                        all_subscribers.add(user_id)

                notification_pairs.append((category, subcategory))

        if not all_subscribers:
            logger.debug(
                f"No subscribers for item {item.get('message_id')} "
                f"with classifications: {classifications}"
            )
            return

        public_link = self._convert_to_public_link(link, channel_name)
        success_count = 0

        for user_id in all_subscribers:
            notification_text = self._format_notification_multi(
                notification_pairs, public_link, channel_name
            )
            keyboard = self._create_unsubscribe_keyboard_multi(notification_pairs)

            success = await self.send_notification(
                user_id, notification_text, reply_markup=keyboard
            )

            if success:
                success_count += 1

            await asyncio.sleep(0.1)

        logger.info(
            f"Category notifications sent: {success_count}/{len(all_subscribers)} "
            f"for {classifications} in channel {channel_name}"
        )

    async def notify_keyword_subscribers(self, item: dict) -> None:
        """Send keyword-based notifications (parallel to category notifications)."""
        text = item.get("text", "")
        link = item.get("tg_link", "")

        if not text:
            return

        # Get all users with keyword subscriptions
        subscribers = await self.mongo.get_all_keyword_subscribers()

        if not subscribers:
            return

        public_link = self._convert_to_public_link(link)
        success_count = 0

        for subscriber in subscribers:
            user_id = subscriber.get("user_id")
            keywords = subscriber.get("keywords", [])

            if not user_id or not keywords:
                continue

            # Check if any keywords match
            matched_keywords = self._match_keywords(text, keywords)

            if matched_keywords:
                notification_text = self._format_notification(
                    ",".join(matched_keywords), "", public_link
                )
                keyboard = self._create_keyword_unsubscribe_keyboard(matched_keywords)

                success = await self.send_notification(
                    user_id, notification_text, reply_markup=keyboard
                )

                if success:
                    success_count += 1

                await asyncio.sleep(0.1)

        if success_count > 0:
            logger.info(
                f"Keyword notifications sent: {success_count} users "
                f"for message {item.get('message_id')}"
            )

    async def notify_new_items_batch(self, items: list[dict]) -> None:
        for item in items:
            try:
                # Send both category and keyword notifications in parallel
                await self.notify_new_item(item)
                await self.notify_keyword_subscribers(item)
            except Exception as e:
                logger.error(
                    f"Error sending notification for item {item.get('message_id')}: {e}"
                )

    def _convert_to_public_link(self, private_link: str, channel_name: str = "") -> str:
        if not private_link:
            return private_link

        if "/c/" in private_link:
            parts = private_link.split("/")
            if len(parts) >= 2:
                message_id = parts[-1]
                if channel_name:
                    return f"https://t.me/{channel_name}/{message_id}"
                return f"https://t.me/baraholka_dubai/{message_id}"

        return private_link

    def _match_keywords(self, text: str, keywords: list[str]) -> list[str]:
        """Match keywords in text using stemming for better matching."""
        from src.infrastructure.mongo import normalize_keyword

        text_lower = text.lower()
        # Split text into words and normalize them
        text_words = text_lower.split()
        text_stems = {normalize_keyword(word) for word in text_words}

        matched = []
        for keyword in keywords:
            keyword_stem = normalize_keyword(keyword)
            # Check if keyword stem matches any word stem in text
            if keyword_stem in text_stems or any(
                keyword_stem in word for word in text_words
            ):
                matched.append(keyword)

        return matched

    def _format_notification_multi(
        self, pairs: list[tuple[str, str]], link: str, channel_name: str
    ) -> str:
        message = "🔔 <b>Новое объявление</b>\n\n"

        for category, subcategory in pairs:
            message += f"📁 <b>{category}:</b> {subcategory}\n"

        message += "\n"

        if link:
            message += f"{link}\n\n"

        if channel_name:
            channel_link = f"https://t.me/{channel_name}"
            message += (
                f"📡 <b>Канал:</b> <a href='{channel_link}'>{channel_name}</a>\n\n"
            )

        return message

    def _format_notification(self, category: str, subcategory: str, link: str) -> str:
        message = "🔔 <b>Новое объявление</b>\n\n"
        message += f"📁 <b>{category}</b>"

        if subcategory:
            message += f"\n   └ {subcategory}"

        message += "\n\n"

        if link:
            message += f"{link}"

        return message

    def _create_unsubscribe_keyboard_multi(
        self, pairs: list[tuple[str, str]]
    ) -> InlineKeyboardMarkup | None:
        from src.tg.bot import CATEGORY_IDS, SUBCATEGORY_IDS

        if not pairs:
            return None

        keyboard = []

        for category, subcategory in pairs[:3]:
            cat_id = CATEGORY_IDS.get(category)
            subcat_id = SUBCATEGORY_IDS.get(category, {}).get(subcategory)

            if cat_id is not None and subcat_id is not None:
                callback_data = f"notif_{cat_id}_{subcat_id}"
                button_text = f"🔕 {category} → {subcategory}"
                if len(button_text) > 40:
                    button_text = f"🔕 {category[:15]}... → {subcategory[:15]}..."
                keyboard.append(
                    [InlineKeyboardButton(button_text, callback_data=callback_data)]
                )

        return InlineKeyboardMarkup(keyboard) if keyboard else None

    def _create_keyword_unsubscribe_keyboard(
        self, matched_keywords: list[str]
    ) -> InlineKeyboardMarkup:
        """Create keyboard with unsubscribe buttons for matched keywords."""
        keyboard = []

        # Add button for first matched keyword (Telegram has callback_data limit)
        if matched_keywords:
            keyword = matched_keywords[0]
            # Limit keyword length in callback_data (max 64 bytes)
            safe_keyword = keyword[:30]
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🔕 Отписаться от: {keyword}",
                        callback_data=f"kw_notif_{safe_keyword}",
                    )
                ]
            )

        return InlineKeyboardMarkup(keyboard)

    def _create_unsubscribe_keyboard(
        self, category: str, subcategory: str
    ) -> InlineKeyboardMarkup | None:
        """Create inline keyboard with unsubscribe button."""
        # Import here to avoid circular dependency
        from src.tg.bot import CATEGORY_IDS, SUBCATEGORY_IDS

        cat_id = CATEGORY_IDS.get(category)
        subcat_id = SUBCATEGORY_IDS.get(category, {}).get(subcategory)

        if cat_id is None or subcat_id is None:
            logger.warning(
                f"Could not create unsubscribe button for {category} → {subcategory}"
            )
            return None

        # Format: notif_{cat_id}_{subcat_id}
        callback_data = f"notif_{cat_id}_{subcat_id}"

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔕 Отписаться от этой категории", callback_data=callback_data
                )
            ]
        ]

        return InlineKeyboardMarkup(keyboard)

    async def close(self) -> None:
        if self.mongo.client:
            self.mongo.client.close()
