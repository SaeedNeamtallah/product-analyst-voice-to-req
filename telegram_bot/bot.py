"""
Tawasul Telegram Bot.
Main bot application using pyTelegramBotAPI.
"""
from __future__ import annotations

import atexit
from pathlib import Path
import tempfile
import telebot
from telegram_bot.config import bot_settings
from telegram_bot import handlers
import logging

try:
    import msvcrt  # Windows
except Exception:  # noqa: BLE001
    msvcrt = None

try:
    import fcntl  # Unix
except Exception:  # noqa: BLE001
    fcntl = None

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

_instance_lock_file = None


def _release_instance_lock() -> None:
    global _instance_lock_file
    if _instance_lock_file is None:
        return
    try:
        _instance_lock_file.seek(0)
        if msvcrt is not None:
            msvcrt.locking(_instance_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        elif fcntl is not None:
            fcntl.flock(_instance_lock_file.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        _instance_lock_file.close()
    except Exception:
        pass
    _instance_lock_file = None


def _acquire_instance_lock() -> bool:
    global _instance_lock_file
    lock_path = Path(tempfile.gettempdir()) / "tawasul_telegram_bot.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fp = open(lock_path, "a+", encoding="utf-8")
    fp.seek(0)

    try:
        if msvcrt is not None:
            msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        elif fcntl is not None:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            fp.close()
            return True
    except Exception:
        fp.close()
        return False

    fp.seek(0)
    fp.truncate(0)
    fp.write("tawasul telegram bot lock\n")
    fp.flush()
    _instance_lock_file = fp
    atexit.register(_release_instance_lock)
    return True

# Initialize bot
bot = telebot.TeleBot(bot_settings.telegram_bot_token)

def print_bot_link():
    """Print bot link to console."""
    try:
        bot_info = bot.get_me()
        bot_link = f"https://t.me/{bot_info.username}"
        logger.info(f"Bot is running! Share this link: {bot_link}")
    except Exception as e:
        logger.error(f"Error getting bot info: {str(e)}")

def setup_handlers():
    """Register all handlers."""
    # Pass bot instance to handlers
    handlers.set_bot(bot)
    
    # Command handlers
    bot.message_handler(commands=['start'])(handlers.start_command)
    bot.message_handler(commands=['help'])(handlers.help_command)
    bot.message_handler(commands=['projects'])(handlers.projects_command)
    bot.message_handler(commands=['newproject'])(handlers.newproject_command)
    bot.message_handler(commands=['srsnow'])(handlers.srsnow_command)

    # Callback handlers
    bot.callback_query_handler(func=lambda call: str(call.data or '').startswith('project:'))(handlers.handle_project_selection)
    bot.callback_query_handler(func=lambda call: str(call.data or '').startswith('srs:'))(handlers.handle_srs_action)
    
    # Voice/audio handlers
    bot.message_handler(content_types=['voice'])(handlers.handle_voice)
    bot.message_handler(content_types=['audio'])(handlers.handle_voice)

    # Text message handler (for queries)
    bot.message_handler(func=lambda message: True)(handlers.handle_message)

def main():
    """Start the bot."""
    if not _acquire_instance_lock():
        logger.error("Another local Telegram bot instance is already running. Stop it before starting a new one.")
        return

    setup_handlers()
    print_bot_link()
    logger.info("Starting Tawasul Telegram Bot (infinity_polling)...")
    try:
        bot.infinity_polling()
    finally:
        _release_instance_lock()

if __name__ == "__main__":
    main()
