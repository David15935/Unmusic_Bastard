# bot/main.py
import logging
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, InlineQueryHandler
from config.config import BOT_TOKEN
from bot.handlers import (
    start, search_cmd, play_cmd, download_cmd, lyrics_cmd, info_cmd,
    queue_cmd, skip_cmd, pause_cmd, resume_cmd, stop_cmd, trending_cmd,
    inline_search
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

async def set_commands(app):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("search", "Search songs"),
        BotCommand("play", "Play and queue a song"),
        BotCommand("download", "Download a song"),
        BotCommand("lyrics", "Get lyrics"),
        BotCommand("info", "Song metadata"),
        BotCommand("queue", "Show queue"),
        BotCommand("skip", "Skip current song"),
        BotCommand("pause", "Pause playback"),
        BotCommand("resume", "Resume playback"),
        BotCommand("stop", "Clear queue"),
        BotCommand("trending", "Trending songs"),
    ]
    await app.bot.set_my_commands(commands)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("play", play_cmd))
    app.add_handler(CommandHandler("download", download_cmd))
    app.add_handler(CommandHandler("lyrics", lyrics_cmd))
    app.add_handler(CommandHandler("info", info_cmd))
    app.add_handler(CommandHandler("queue", queue_cmd))
    app.add_handler(CommandHandler("skip", skip_cmd))
    app.add_handler(CommandHandler("pause", pause_cmd))
    app.add_handler(CommandHandler("resume", resume_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("trending", trending_cmd))

    app.add_handler(InlineQueryHandler(inline_search))

    app.post_init = set_commands

    logger.info("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
