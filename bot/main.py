import importlib.util
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.handlers import (
    button_handler,
    download,
    error_handler,
    info,
    log_update,
    lyrics,
    play,
    playlist,
    resume,
    show_queue,
    skip,
    start,
    trending,
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "bot.log"
CONFIG_FILE = BASE_DIR / "config" / "config.py"

LOCAL_BOT_API_URL = os.getenv("LOCAL_BOT_API_URL")
LOCAL_BOT_API_FILE_URL = os.getenv("LOCAL_BOT_API_FILE_URL")


def _read_token_from_config() -> Optional[str]:
    if not CONFIG_FILE.exists():
        return None

    spec = importlib.util.spec_from_file_location("bot_local_config", str(CONFIG_FILE))
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "BOT_TOKEN", None)


def _get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        token = _read_token_from_config()
    if not token:
        raise RuntimeError("BOT_TOKEN not set. Add it to .env or config/config.py")
    return token


def _configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


async def set_commands(app: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("play", "Search and play a song"),
        BotCommand("download", "Download a song"),
        BotCommand("lyrics", "Get song lyrics"),
        BotCommand("info", "Get song info"),
        BotCommand("trending", "Show trending songs"),
        BotCommand("queue", "Show current queue"),
        BotCommand("skip", "Skip to next queued song"),
        BotCommand("playlist", "Manage playlists"),
        BotCommand("resume", "Resume pending upload"),
    ]
    await app.bot.set_my_commands(commands)


def build_app() -> Application:
    token = _get_bot_token()
    builder = ApplicationBuilder().token(token)

    if LOCAL_BOT_API_URL:
        builder = builder.base_url(LOCAL_BOT_API_URL)
        if LOCAL_BOT_API_FILE_URL:
            builder = builder.base_file_url(LOCAL_BOT_API_FILE_URL)
        builder = builder.local_mode(True)

    app = builder.build()

    app.add_handler(MessageHandler(filters.ALL, log_update, block=False), group=1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(CommandHandler("lyrics", lyrics))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("trending", trending))
    app.add_handler(CommandHandler("queue", show_queue))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(CommandHandler("playlist", playlist))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_error_handler(error_handler)
    app.post_init = set_commands
    return app


def main() -> None:
    _configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Music Bot...")
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
