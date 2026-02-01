"""Common handlers: /start, /help, /cancel, /whoami, /channelinfo."""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberAdministrator, ChatMemberOwner
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.bot import bot
from app.config import get_settings

logger = logging.getLogger(__name__)

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    logger.info(f"User {message.from_user.id} started the bot")
    
    settings = get_settings()
    is_admin = message.from_user.id in settings.admin_ids
    
    admin_commands = ""
    if is_admin:
        admin_commands = (
            "\n\n👑 <b>Админ-команды:</b>\n"
            "/allposts — посты всех пользователей\n"
        )
    
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Я бот для создания и планирования публикаций в канал.\n\n"
        "📝 <b>Команды:</b>\n"
        "/new — создать новый пост\n"
        "/posts — все мои посты\n"
        "/drafts — черновики\n"
        "/scheduled — запланированные посты\n"
        "/edit &lt;ID&gt; — редактировать пост\n"
        "/whoami — информация о вас\n"
        "/channelinfo — информация о канале\n"
        "/help — справка\n"
        "/cancel — отмена текущего действия"
        f"{admin_commands}"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    settings = get_settings()
    is_admin = message.from_user.id in settings.admin_ids
    
    admin_help = ""
    if is_admin:
        admin_help = (
            "\n\n👑 <b>Админ-команды:</b>\n"
            "/allposts — посты всех пользователей\n"
            "Можно редактировать чужие посты через /edit &lt;ID&gt;"
        )
    
    await message.answer(
        "📚 <b>Справка</b>\n\n"
        "<b>Создание поста:</b>\n"
        "1. Отправьте /new для создания нового поста\n"
        "2. Отправьте текст или фото с подписью\n"
        "3. Добавьте ещё медиа для альбома (опционально)\n"
        "4. Добавьте кнопки со ссылками\n"
        "5. Выберите время публикации или опубликуйте сразу\n\n"
        "<b>Управление постами:</b>\n"
        "/posts — все ваши посты\n"
        "/drafts — только черновики\n"
        "/scheduled — запланированные посты\n"
        "/edit &lt;ID&gt; — редактировать опубликованный пост\n\n"
        "<b>Информация:</b>\n"
        "/whoami — информация о вашем аккаунте\n"
        "/channelinfo — информация о канале и правах бота\n\n"
        "<b>Формат времени:</b>\n"
        "• <code>сейчас</code> — немедленно\n"
        "• <code>15:30</code> — сегодня в 15:30\n"
        "• <code>завтра 15:30</code> — завтра в 15:30\n"
        "• <code>25.01 15:30</code> — конкретная дата"
        f"{admin_help}"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Handle /cancel command."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("✅ Действие отменено.")
    logger.info(f"User {message.from_user.id} cancelled state {current_state}")


@router.message(Command("whoami"))
async def cmd_whoami(message: Message) -> None:
    """Handle /whoami command - show user info and config."""
    settings = get_settings()
    user = message.from_user

    # Build full name
    full_name = user.full_name or ""
    username_str = f"@{user.username}" if user.username else "<i>не задан</i>"

    await message.answer(
        "👤 <b>Информация о вас</b>\n\n"
        f"<b>User ID:</b> <code>{user.id}</code>\n"
        f"<b>Username:</b> {username_str}\n"
        f"<b>Полное имя:</b> {full_name}\n\n"
        "⚙️ <b>Настройки бота</b>\n\n"
        f"<b>Timezone:</b> <code>{settings.tz}</code>\n"
        f"<b>Channel ID:</b> <code>{settings.channel_id}</code>"
    )
    logger.info(f"User {user.id} requested /whoami")


@router.message(Command("channelinfo"))
async def cmd_channelinfo(message: Message) -> None:
    """Handle /channelinfo command - show channel info and bot permissions."""
    settings = get_settings()
    channel_id = settings.channel_id

    try:
        # Get channel info
        chat = await bot.get_chat(channel_id)

        # Build channel info
        username_str = f"@{chat.username}" if chat.username else "<i>приватный</i>"

        response = (
            "📢 <b>Информация о канале</b>\n\n"
            f"<b>Title:</b> {chat.title}\n"
            f"<b>Username:</b> {username_str}\n"
            f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
            f"<b>Type:</b> {chat.type}\n\n"
        )

        # Check bot permissions
        try:
            bot_info = await bot.get_me()
            member = await bot.get_chat_member(chat.id, bot_info.id)

            if isinstance(member, ChatMemberOwner):
                response += (
                    "🤖 <b>Статус бота:</b> 👑 Владелец\n\n"
                    "✅ Полные права"
                )
            elif isinstance(member, ChatMemberAdministrator):
                # Check specific permissions
                can_post = "✅" if member.can_post_messages else "❌"
                can_edit = "✅" if member.can_edit_messages else "❌"
                can_delete = "✅" if member.can_delete_messages else "❌"
                can_invite = "✅" if member.can_invite_users else "❌"

                response += (
                    "🤖 <b>Статус бота:</b> 👮 Администратор\n\n"
                    "<b>Права:</b>\n"
                    f"{can_post} Публикация сообщений (can_post_messages)\n"
                    f"{can_edit} Редактирование сообщений (can_edit_messages)\n"
                    f"{can_delete} Удаление сообщений (can_delete_messages)\n"
                    f"{can_invite} Приглашение пользователей (can_invite_users)"
                )

                # Warn if missing critical permissions
                if not member.can_post_messages or not member.can_edit_messages:
                    response += (
                        "\n\n⚠️ <b>Внимание:</b> Для корректной работы боту нужны "
                        "права на публикацию и редактирование сообщений!"
                    )
            else:
                response += (
                    "🤖 <b>Статус бота:</b> ❌ Не администратор\n\n"
                    "⚠️ <b>Бот не является администратором канала!</b>\n\n"
                    "Для работы добавьте бота админом с правами:\n"
                    "• Публикация сообщений\n"
                    "• Редактирование сообщений"
                )

        except TelegramBadRequest as e:
            response += f"🤖 <b>Статус бота:</b> ❓ Не удалось проверить\n\n<i>Ошибка: {e.message}</i>"

        await message.answer(response)
        logger.info(f"User {message.from_user.id} requested /channelinfo for {chat.id}")

    except TelegramBadRequest as e:
        error_msg = (
            "❌ <b>Ошибка получения информации о канале</b>\n\n"
            f"<b>Channel ID:</b> <code>{channel_id}</code>\n"
            f"<b>Ошибка:</b> {e.message}\n\n"
            "💡 <b>Возможные причины:</b>\n"
            "• Неверный CHANNEL_ID в конфиге\n"
            "• Бот не добавлен в канал\n"
            "• Канал не существует"
        )
        await message.answer(error_msg)
        logger.error(f"Failed to get channel info: {e}")

    except TelegramForbiddenError as e:
        error_msg = (
            "🚫 <b>Нет доступа к каналу</b>\n\n"
            f"<b>Channel ID:</b> <code>{channel_id}</code>\n\n"
            "💡 <b>Решение:</b>\n"
            "1. Откройте настройки канала\n"
            "2. Перейдите в «Администраторы»\n"
            "3. Добавьте бота администратором\n"
            "4. Включите права:\n"
            "   • ✅ Публикация сообщений\n"
            "   • ✅ Редактирование сообщений"
        )
        await message.answer(error_msg)
        logger.error(f"Forbidden access to channel: {e}")
