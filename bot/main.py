import logging
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler
from bot.handlers import start, play, download, info, error_handler

from config.config import BOT_TOKEN

# ---------- LOGGING ----------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- REGISTER COMMANDS ----------
async def set_commands(app):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("play", "Play a song"),
        BotCommand("download", "Download a song"),
        BotCommand("info", "Get song info"),
    ]
    await app.bot.set_my_commands(commands)

# ---------- MAIN ----------
def main():
    logger.info("Starting Music Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("download", download))
    app.add_handler(CommandHandler("info", info))

    # Error handler
    app.add_error_handler(error_handler)

    # Set Bot commands in Telegram menu
    app.post_init = set_commands

    # Run bot
    app.run_polling()

if __name__ == "__main__":
    main()
