import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from bot.handlers import (
    log_update,
    start,
    play,
    download,
    lyrics,
    info,
    trending,
    show_queue,
    skip,
    playlist,
    button_handler,
    error_handler,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOCAL_BOT_API_URL = os.getenv("LOCAL_BOT_API_URL")
LOCAL_BOT_API_FILE_URL = os.getenv("LOCAL_BOT_API_FILE_URL")
if not BOT_TOKEN:
    try:
        from config.config import BOT_TOKEN as CONFIG_TOKEN

        BOT_TOKEN = CONFIG_TOKEN
    except Exception:
        BOT_TOKEN = None

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set. Add it to .env or config/config.py")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "bot.log"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def set_commands(app):
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
    ]
    await app.bot.set_my_commands(commands)


def build_app():
    builder = ApplicationBuilder().token(BOT_TOKEN)
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

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_error_handler(error_handler)
    app.post_init = set_commands

    return app


def main():
    logger.info("Starting Music Bot...")
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
