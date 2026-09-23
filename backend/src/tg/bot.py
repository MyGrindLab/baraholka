from pycommontools.configs.logging import setup_logger
from pycommontools.resources.singleton import Singleton
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.core.categories import CATEGORIES
from src.core.settings import settings
from src.infrastructure.mongo import MongoDBRepository
from src.services.channels import ChannelService

logger = setup_logger("bot")

# Создаем маппинг категорий и подкатегорий на короткие ID
CATEGORY_IDS = {cat: str(idx) for idx, cat in enumerate(CATEGORIES.keys())}
ID_TO_CATEGORY = {v: k for k, v in CATEGORY_IDS.items()}

# Создаем маппинг подкатегорий на короткие ID для каждой категории
SUBCATEGORY_IDS = {}
ID_TO_SUBCATEGORY = {}

for cat_idx, (category, subcategories) in enumerate(CATEGORIES.items()):
    SUBCATEGORY_IDS[category] = {
        subcat: str(subcat_idx) for subcat_idx, subcat in enumerate(subcategories)
    }
    ID_TO_SUBCATEGORY[str(cat_idx)] = {
        str(subcat_idx): subcat for subcat_idx, subcat in enumerate(subcategories)
    }


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает главное меню с кнопками команд."""
    keyboard = [
        [KeyboardButton("🔔 Подписаться"), KeyboardButton("🔕 Отписаться")],
        [KeyboardButton("🔑 Ключевые слова"), KeyboardButton("📡 Каналы")],
        [KeyboardButton("📋 Мои подписки"), KeyboardButton("❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


class SubscriptionBot(metaclass=Singleton):
    def __init__(self) -> None:
        self.mongo = MongoDBRepository()
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user

        if not user:
            raise ValueError("User information is missing")

        await self.mongo.ensure_user(user.id, user.username or user.first_name)

        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Я бот для уведомлений о новых объявлениях на Baraholka Dubai.\n\n"
            "🌐 Просматривайте все объявления на <a href='https://baraholka.org'>baraholka.org</a>\n\n"
            "Используйте кнопки меню ниже или команды:\n"
            "/subscribe - Подписаться на категории\n"
            "/unsubscribe - Отписаться от категорий\n"
            "/keywords - Управление ключевыми словами\n"
            "/channels - Выбрать каналы\n"
            "/list - Посмотреть свои подписки\n"
            "/help - Помощь\n"
        )
        await update.message.reply_text(
            welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - помощь."""
        help_text = (
            "📚 Помощь по использованию бота\n\n"
            "🌐 Просматривайте объявления на <a href='https://baraholka.org'>baraholka.org</a>\n\n"
            "🔔 /subscribe - Подписаться на категории\n"
            "Выберите категории, о которых хотите получать уведомления.\n\n"
            "🔕 /unsubscribe - Отписаться от категорий\n"
            "Отмените подписку на категории.\n\n"
            "🔑 /keywords - Управление ключевыми словами\n"
            "Добавьте слова, и получайте уведомления при их упоминании.\n\n"
            "📡 /channels - Выбрать каналы\n"
            "Выберите каналы, от которых хотите получать уведомления.\n"
            "Если не выбрано ни одного канала - уведомления приходят от всех.\n\n"
            "📋 /list - Список ваших подписок\n"
            "Посмотрите, на какие категории вы подписаны.\n\n"
            "При появлении нового объявления в выбранной категории "
            "или с вашим ключевым словом вы получите уведомление."
        )
        await update.message.reply_text(
            help_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML"
        )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /cancel - отмена текущей операции."""
        context.user_data.clear()
        await update.message.reply_text(
            "Операция отменена.", reply_markup=get_main_menu_keyboard()
        )

    async def subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /subscribe - показать категории для подписки."""
        user_id = update.effective_user.id

        # Получаем текущие подписки пользователя
        subscriptions = await self.mongo.get_user_subscriptions(user_id)
        user_subscriptions = subscriptions.get("subscriptions", {})

        # Создаем клавиатуру с категориями
        keyboard = []
        for category in CATEGORIES.keys():
            # Подсчитываем подписки в этой категории
            subscribed_count = len(user_subscriptions.get(category, []))
            total_count = len(CATEGORIES[category])

            if subscribed_count == 0:
                emoji = "⬜"
                button_text = f"{emoji} {category}"
            elif subscribed_count == total_count:
                emoji = "✅"
                button_text = f"{emoji} {category}"
            else:
                emoji = "🔵"
                button_text = f"{emoji} {category} ({subscribed_count}/{total_count})"

            # Используем короткий ID вместо полного названия
            cat_id = CATEGORY_IDS[category]
            callback_data = f"sc_{cat_id}"

            keyboard.append(
                [InlineKeyboardButton(button_text, callback_data=callback_data)]
            )

        # Добавляем кнопку "Готово"
        keyboard.append([InlineKeyboardButton("✔️ Готово", callback_data="sub_done")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "🔔 Выберите категории для подписки:\n\n"
            "✅ - Все подкатегории выбраны\n"
            "🔵 - Частично выбрано\n"
            "⬜ - Не выбрано\n\n"
            "Нажмите на категорию, чтобы выбрать подкатегории."
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

    async def show_subcategories(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str
    ):
        """Показать подкатегории для выбранной категории."""
        user_id = update.effective_user.id

        # Получаем текущие подписки пользователя
        subscriptions = await self.mongo.get_user_subscriptions(user_id)
        user_subscriptions = subscriptions.get("subscriptions", {})
        category_subs = user_subscriptions.get(category, [])

        # Создаем клавиатуру с подкатегориями
        keyboard = []
        subcategories = CATEGORIES.get(category, [])
        cat_id = CATEGORY_IDS[category]

        for subcategory in subcategories:
            # Помечаем подписанные подкатегории
            emoji = "✅" if subcategory in category_subs else "⬜"
            button_text = f"{emoji} {subcategory}"

            # Используем короткие ID: ss_{cat_id}_{subcat_id}
            subcat_id = SUBCATEGORY_IDS[category][subcategory]
            callback_data = f"ss_{cat_id}_{subcat_id}"

            keyboard.append(
                [InlineKeyboardButton(button_text, callback_data=callback_data)]
            )

        # Добавляем кнопки управления
        keyboard.append(
            [
                InlineKeyboardButton("✔️ Выбрать все", callback_data=f"sa_{cat_id}"),
                InlineKeyboardButton("✖️ Очистить все", callback_data=f"sn_{cat_id}"),
            ]
        )
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="sub_back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            f'🔔 Подкатегории в категории "{category}":\n\n'
            "✅ - Вы подписаны\n"
            "⬜ - Не подписаны\n\n"
            "Выберите подкатегории для подписки."
        )

        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /unsubscribe - показать категории для отписки."""
        user_id = update.effective_user.id

        # Получаем текущие подписки пользователя
        subscriptions = await self.mongo.get_user_subscriptions(user_id)
        user_subscriptions = subscriptions.get("subscriptions", {})

        if not user_subscriptions:
            await update.message.reply_text(
                "У вас нет активных подписок.\n"
                "Используйте /subscribe чтобы подписаться на категории."
            )
            return

        # Создаем клавиатуру только с подписанными категориями
        keyboard = []
        for category, subcategories in user_subscriptions.items():
            if subcategories:
                count = len(subcategories)
                button_text = f"❌ {category} ({count})"
                cat_id = CATEGORY_IDS[category]
                callback_data = f"uc_{cat_id}"
                keyboard.append(
                    [InlineKeyboardButton(button_text, callback_data=callback_data)]
                )

        # Добавляем кнопку "Отменить"
        keyboard.append(
            [InlineKeyboardButton("↩️ Отменить", callback_data="unsub_cancel")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "🔕 Выберите категорию для отписки:"

        await update.message.reply_text(text, reply_markup=reply_markup)

    async def show_unsubscribe_subcategories(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str
    ):
        """Показать подкатегории для отписки."""
        user_id = update.effective_user.id

        # Получаем текущие подписки пользователя
        subscriptions = await self.mongo.get_user_subscriptions(user_id)
        user_subscriptions = subscriptions.get("subscriptions", {})
        category_subs = user_subscriptions.get(category, [])

        if not category_subs:
            await update.callback_query.answer("Нет подписок в этой категории")
            return

        # Создаем клавиатуру с подкатегориями
        keyboard = []
        cat_id = CATEGORY_IDS[category]

        for subcategory in category_subs:
            button_text = f"❌ {subcategory}"
            subcat_id = SUBCATEGORY_IDS[category][subcategory]
            callback_data = f"us_{cat_id}_{subcat_id}"
            keyboard.append(
                [InlineKeyboardButton(button_text, callback_data=callback_data)]
            )

        # Добавляем кнопки управления
        keyboard.append(
            [InlineKeyboardButton("✖️ Отписаться от всех", callback_data=f"ua_{cat_id}")]
        )
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="unsub_back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            f'🔕 Ваши подписки в категории "{category}":\n\n'
            "Выберите подкатегории для отписки."
        )

        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def list_subscriptions(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Команда /list - показать подписки пользователя."""
        user_id = update.effective_user.id

        subscriptions = await self.mongo.get_user_subscriptions(user_id)
        user_subscriptions = subscriptions.get("subscriptions", {})
        keywords = await self.mongo.get_user_keywords(user_id)
        channels = await self.mongo.get_user_channels(user_id)

        has_subs = bool(user_subscriptions)
        has_keywords = bool(keywords)
        has_channels = bool(channels)

        if not has_subs and not has_keywords and not has_channels:
            text = (
                "У вас нет активных подписок.\n\n"
                "Используйте /subscribe для подписки на категории\n"
                "или /keywords для добавления ключевых слов\n"
                "или /channels для выбора каналов."
            )
        else:
            text = "📋 Ваши подписки:\n\n"

            if has_subs:
                text += "📁 <b>Категории:</b>\n"
                for category, subcategories in user_subscriptions.items():
                    if subcategories:
                        text += f"  • {category}:\n"
                        for subcategory in subcategories:
                            text += f"    - {subcategory}\n"
                text += "\n"

            if has_keywords:
                text += f"🔑 <b>Ключевые слова ({len(keywords)}):</b>\n"
                for kw in keywords:
                    text += f"  • {kw}\n"
                text += "\n"

            if has_channels:
                text += f"📡 <b>Каналы ({len(channels)}):</b>\n"
                for ch in channels:
                    text += f"  • {ch}\n"
            else:
                text += "📡 <b>Каналы:</b> Все каналы\n"

        await update.message.reply_text(text, parse_mode="HTML")

    async def manage_keywords(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Manage keyword subscriptions."""
        user_id = update.effective_user.id
        keywords = await self.mongo.get_user_keywords(user_id)

        keyboard = []

        # Show existing keywords with remove buttons
        if keywords:
            for keyword in keywords:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"❌ {keyword}", callback_data=f"kw_remove_{keyword}"
                        )
                    ]
                )

        # Add buttons for adding new keyword and done
        keyboard.append(
            [InlineKeyboardButton("➕ Добавить ключевое слово", callback_data="kw_add")]
        )
        keyboard.append([InlineKeyboardButton("✔️ Готово", callback_data="kw_done")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "🔑 <b>Ключевые слова</b>\n\n"
            "Вы будете получать уведомления, когда в объявлении встретится "
            "одно из ваших ключевых слов.\n\n"
        )

        if keywords:
            text += f"📝 Ваши ключевые слова ({len(keywords)}):\n"
            for kw in keywords:
                text += f"  • {kw}\n"
            text += "\nНажмите на слово, чтобы удалить его."
        else:
            text += "У вас пока нет ключевых слов.\n"
            text += 'Нажмите "➕ Добавить" чтобы добавить.'

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=reply_markup, parse_mode="HTML"
            )

    async def request_keyword(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Request user to send a keyword."""
        # Set state to expect keyword input
        context.user_data["awaiting_keyword"] = True

        await update.callback_query.edit_message_text(
            "🔑 Отправьте ключевое слово, которое хотите добавить.\n\n"
            "Например: <code>iPhone</code>, <code>квартира</code>, "
            "<code>авто</code>\n\n"
            "Отправьте /cancel чтобы отменить.",
            parse_mode="HTML",
        )

    async def manage_channels(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user_id = update.effective_user.id
        user_channels = await self.mongo.get_user_channels(user_id)

        channel_service = ChannelService()
        all_channels = await channel_service.get_all_channels()

        keyboard = []

        for channel in all_channels:
            channel_name = channel["name"]
            is_selected = channel_name in user_channels
            emoji = "✅" if is_selected else "⬜"
            button_text = f"{emoji} {channel_name}"

            keyboard.append(
                [
                    InlineKeyboardButton(
                        button_text, callback_data=f"ch_toggle_{channel_name}"
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton("✔️ Выбрать все", callback_data="ch_select_all"),
                InlineKeyboardButton("✖️ Очистить все", callback_data="ch_clear_all"),
            ]
        )
        keyboard.append([InlineKeyboardButton("✔️ Готово", callback_data="ch_done")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "📡 <b>Выбор каналов</b>\n\n"
            "Выберите каналы, от которых хотите получать уведомления.\n\n"
            "✅ - Выбран\n"
            "⬜ - Не выбран\n\n"
        )

        if user_channels:
            text += f"📝 Вы подписаны на каналы ({len(user_channels)}):\n"
            for ch in user_channels:
                text += f"  • {ch}\n"
            text += "\n"
        else:
            text += "📌 Каналы не выбраны - уведомления будут приходить от <b>всех каналов</b>.\n\n"

        text += "Нажмите на канал, чтобы включить/выключить его."

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=reply_markup, parse_mode="HTML"
            )

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Обработка текстовых сообщений от пользователя."""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        text = update.message.text.strip()

        # Check if we're waiting for keyword input
        if context.user_data.get("awaiting_keyword"):
            keyword = text.lower().strip()

            # Validate keyword (не пустое, не слишком длинное)
            if not keyword:
                await update.message.reply_text(
                    "❌ Ключевое слово не может быть пустым. Попробуйте снова."
                )
                return

            if len(keyword) > 50:
                await update.message.reply_text(
                    "❌ Ключевое слово слишком длинное (максимум 50 символов)."
                )
                return

            # Add keyword
            await self.mongo.add_keyword(user_id, keyword)
            context.user_data["awaiting_keyword"] = False

            await update.message.reply_text(
                f"✅ Ключевое слово добавлено: <b>{keyword}</b>",
                parse_mode="HTML",
            )

            # Show keywords management again
            await self.manage_keywords(update, context)
            return

        # Handle menu buttons
        if text == "🔔 Подписаться":
            await self.subscribe(update, context)
        elif text == "🔕 Отписаться":
            await self.unsubscribe(update, context)
        elif text == "🔑 Ключевые слова":
            await self.manage_keywords(update, context)
        elif text == "📡 Каналы":
            await self.manage_channels(update, context)
        elif text == "📋 Мои подписки":
            await self.list_subscriptions(update, context)
        elif text == "❓ Помощь":
            await self.help_command(update, context)
        else:
            response = (
                "Извините, я не понимаю это сообщение. 🤔\n\n"
                "Используйте /help для получения помощи.\n\n"
            )
            await update.message.reply_text(
                response, reply_markup=get_main_menu_keyboard()
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на inline кнопки."""
        query = update.callback_query
        if not query or not query.data or not update.effective_user:
            return

        await query.answer()

        user_id = update.effective_user.id
        data = query.data

        # Подписка
        if data.startswith("sc_"):
            # Показать подкатегории для выбранной категории
            cat_id = data.replace("sc_", "")
            category = ID_TO_CATEGORY[cat_id]
            await self.show_subcategories(update, context, category)

        elif data.startswith("ss_"):
            # Переключить подписку на подкатегорию (ss_{cat_id}_{subcat_id})
            parts = data.replace("ss_", "").split("_")
            if len(parts) == 2:
                cat_id, subcat_id = parts
                category = ID_TO_CATEGORY[cat_id]
                subcategory = ID_TO_SUBCATEGORY[cat_id][subcat_id]
                await self.mongo.toggle_subcategory_subscription(
                    user_id, category, subcategory
                )
                # Обновляем клавиатуру
                await self.show_subcategories(update, context, category)

        elif data.startswith("sa_"):
            # Подписаться на все подкатегории в категории
            cat_id = data.replace("sa_", "")
            category = ID_TO_CATEGORY[cat_id]
            subcategories = CATEGORIES.get(category, [])
            for subcategory in subcategories:
                await self.mongo.toggle_subcategory_subscription(
                    user_id, category, subcategory
                )
            # Обновляем клавиатуру
            await self.show_subcategories(update, context, category)

        elif data.startswith("sn_"):
            # Отписаться от всех подкатегорий в категории
            cat_id = data.replace("sn_", "")
            category = ID_TO_CATEGORY[cat_id]
            subscriptions = await self.mongo.get_user_subscriptions(user_id)
            user_subscriptions = subscriptions.get("subscriptions", {})
            category_subs = user_subscriptions.get(category, [])

            for subcategory in category_subs:
                await self.mongo.remove_subcategory_subscription(
                    user_id, category, subcategory
                )
            # Обновляем клавиатуру
            await self.show_subcategories(update, context, category)

        elif data == "sub_back":
            # Вернуться к списку категорий
            await self.subscribe(update, context)

        elif data == "sub_done":
            # Завершение подписки
            subscriptions = await self.mongo.get_user_subscriptions(user_id)
            user_subscriptions = subscriptions.get("subscriptions", {})

            if user_subscriptions:
                text = "✅ Подписки обновлены!\n\nВы подписаны на:\n\n"
                for category, subcategories in user_subscriptions.items():
                    if subcategories:
                        text += f"📁 {category}:\n"
                        for subcategory in subcategories:
                            text += f"  • {subcategory}\n"
                        text += "\n"
            else:
                text = "У вас нет активных подписок."

            await query.edit_message_text(text)

        # Отписка
        elif data.startswith("uc_"):
            # Показать подкатегории для отписки
            cat_id = data.replace("uc_", "")
            category = ID_TO_CATEGORY[cat_id]
            await self.show_unsubscribe_subcategories(update, context, category)

        elif data.startswith("us_"):
            # Отписаться от подкатегории (us_{cat_id}_{subcat_id})
            parts = data.replace("us_", "").split("_")
            if len(parts) == 2:
                cat_id, subcat_id = parts
                category = ID_TO_CATEGORY[cat_id]
                subcategory = ID_TO_SUBCATEGORY[cat_id][subcat_id]
                await self.mongo.remove_subcategory_subscription(
                    user_id, category, subcategory
                )
                # Обновляем клавиатуру
                await self.show_unsubscribe_subcategories(update, context, category)

        elif data.startswith("ua_"):
            # Отписаться от всех подкатегорий в категории
            cat_id = data.replace("ua_", "")
            category = ID_TO_CATEGORY[cat_id]
            subscriptions = await self.mongo.get_user_subscriptions(user_id)
            user_subscriptions = subscriptions.get("subscriptions", {})
            category_subs = user_subscriptions.get(category, [])

            for subcategory in list(category_subs):
                await self.mongo.remove_subcategory_subscription(
                    user_id, category, subcategory
                )

            text = f"✅ Вы отписались от всех подкатегорий в категории: {category}"
            await query.edit_message_text(text)

        elif data == "unsub_back":
            # Вернуться к списку категорий для отписки
            # Нужно создать новое сообщение, так как метод unsubscribe ожидает message
            await query.edit_message_text(
                "↩️ Используйте /unsubscribe чтобы вернуться к списку категорий."
            )

        elif data == "unsub_cancel":
            # Отмена отписки
            await query.edit_message_text("Отписка отменена.")

        elif data.startswith("notif_"):
            # Отписаться от подкатегории из уведомления (notif_{cat_id}_{subcat_id})
            parts = data.replace("notif_", "").split("_")
            if len(parts) == 2:
                cat_id, subcat_id = parts
                category = ID_TO_CATEGORY.get(cat_id)
                subcategory = ID_TO_SUBCATEGORY.get(cat_id, {}).get(subcat_id)

                if category and subcategory:
                    await self.mongo.remove_subcategory_subscription(
                        user_id, category, subcategory
                    )

                    # Show quick confirmation
                    await query.answer(
                        "✅ Отписка выполнена",
                        show_alert=False,
                    )

                    # Get updated subscriptions
                    subscriptions = await self.mongo.get_user_subscriptions(user_id)
                    user_subscriptions = subscriptions.get("subscriptions", {})

                    # Format subscription list
                    if user_subscriptions:
                        text = (
                            "✅ Вы отписались от: "
                            f"<b>{category}</b> → {subcategory}\n\n"
                            "📋 Ваши текущие подписки:\n\n"
                        )
                        for cat, subcats in user_subscriptions.items():
                            if subcats:
                                text += f"📁 <b>{cat}</b>:\n"
                                for subcat in subcats:
                                    text += f"  • {subcat}\n"
                                text += "\n"
                    else:
                        text = (
                            "✅ Вы отписались от: "
                            f"<b>{category}</b> → {subcategory}\n\n"
                            "У вас больше нет активных подписок.\n"
                            "Используйте /subscribe для новых подписок."
                        )

                    # Send new message with updated subscriptions
                    await query.message.reply_text(text, parse_mode="HTML")

                    logger.info(
                        f"User {user_id} unsubscribed from {category} → {subcategory} "
                        "via notification button"
                    )
                else:
                    await query.answer("Ошибка: категория не найдена", show_alert=True)

        # Keyword management
        elif data == "kw_add":
            # Request keyword from user
            await self.request_keyword(update, context)

        elif data.startswith("kw_remove_"):
            # Remove keyword from management UI
            keyword = data.replace("kw_remove_", "")
            await self.mongo.remove_keyword(user_id, keyword)
            await query.answer(f"✅ Удалено: {keyword}", show_alert=False)
            # Refresh keywords list
            await self.manage_keywords(update, context)

        elif data.startswith("kw_notif_"):
            # Remove keyword from notification
            keyword = data.replace("kw_notif_", "")
            await self.mongo.remove_keyword(user_id, keyword)

            # Show confirmation
            await query.answer("✅ Отписка выполнена", show_alert=False)

            # Get updated keywords
            keywords = await self.mongo.get_user_keywords(user_id)

            # Format message with updated keywords list
            if keywords:
                text = (
                    f"✅ Вы отписались от ключевого слова: <b>{keyword}</b>\n\n"
                    f"🔑 Ваши оставшиеся ключевые слова ({len(keywords)}):\n"
                )
                for kw in keywords:
                    text += f"  • {kw}\n"
            else:
                text = (
                    f"✅ Вы отписались от ключевого слова: <b>{keyword}</b>\n\n"
                    "У вас больше нет ключевых слов.\n"
                    "Используйте /keywords для добавления новых."
                )

            # Send new message with updated info
            if query.message:
                await query.message.reply_text(text, parse_mode="HTML")

            logger.info(
                f"User {user_id} unsubscribed from keyword '{keyword}' "
                "via notification button"
            )

        elif data == "kw_done":
            # Finish keyword management
            keywords = await self.mongo.get_user_keywords(user_id)
            if keywords:
                text = f"✅ У вас {len(keywords)} ключевых слов:\n\n"
                for kw in keywords:
                    text += f"  • {kw}\n"
                text += "\n Вы будете получать уведомления о новых объявлениях!"
            else:
                text = "У вас нет ключевых слов."

            await query.edit_message_text(text)

        # Channel management
        elif data.startswith("ch_toggle_"):
            channel_name = data.replace("ch_toggle_", "")
            await self.mongo.toggle_channel(user_id, channel_name)
            await self.manage_channels(update, context)

        elif data == "ch_select_all":
            channel_service = ChannelService()
            all_channels = await channel_service.get_all_channels()
            channel_names = [ch["name"] for ch in all_channels]
            await self.mongo.set_all_channels(user_id, channel_names)
            await self.manage_channels(update, context)

        elif data == "ch_clear_all":
            await self.mongo.clear_all_channels(user_id)
            await self.manage_channels(update, context)

        elif data == "ch_done":
            user_channels = await self.mongo.get_user_channels(user_id)
            if user_channels:
                text = f"✅ Вы подписаны на {len(user_channels)} каналов:\n\n"
                for ch in user_channels:
                    text += f"  • {ch}\n"
                text += "\nВы будете получать уведомления только от выбранных каналов!"
            else:
                text = (
                    "📡 Каналы не выбраны.\n\n"
                    "Вы будете получать уведомления от <b>всех каналов</b>."
                )

            await query.edit_message_text(text, parse_mode="HTML")

    async def setup(self):
        """Настройка бота (регистрация обработчиков)."""
        logger.info("Setting up subscription bot...")

        # Создаем приложение
        self.application = (
            Application.builder().token(settings.telegram_bot_token).build()
        )

        # Регистрируем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("subscribe", self.subscribe))
        self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe))
        self.application.add_handler(CommandHandler("keywords", self.manage_keywords))
        self.application.add_handler(CommandHandler("channels", self.manage_channels))
        self.application.add_handler(CommandHandler("list", self.list_subscriptions))
        self.application.add_handler(CommandHandler("cancel", self.cancel))

        # Регистрируем обработчик callback
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Регистрируем обработчик текстовых сообщений (должен быть последним)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Инициализируем приложение
        await self.application.initialize()
        await self.application.start()

        logger.info("Bot setup complete")

        return self.application

    async def shutdown(self):
        """Остановка бота."""
        if self.application:
            logger.info("Shutting down bot application...")
            await self.application.stop()
            await self.application.shutdown()

        if self.mongo.client:
            self.mongo.client.close()
