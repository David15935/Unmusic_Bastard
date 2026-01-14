import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.music_api import search_song, download_song, get_info

logger = logging.getLogger(__name__)

# ---------- ERROR HANDLER ----------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled exception while handling an update", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text("⚠️ Something went wrong.")

# ---------- COMMAND HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎵 Welcome to Music Bot!\n\n"
        "Commands:\n"
        "/play <song name> - Play a song\n"
        "/download <song name> - Download a song\n"
        "/lyrics <song name> - Get lyrics\n"
        "/info <song name> - Get song info\n"
        "/queue - Show current queue\n"
    )
    await update.message.reply_text(text)

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /play <song name>")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"🎶 Searching for `{query}`...", parse_mode=None)
    song_url = await search_song(query)
    if not song_url:
        await update.message.reply_text("❌ Song not found.")
        return
    await update.message.reply_text(f"▶️ Playing: {query}\n{song_url}")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /download <song name>")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"⬇️ Downloading `{query}`...", parse_mode=None)
    file_path = await download_song(query)
    if not file_path:
        await update.message.reply_text("❌ Failed to download song.")
        return
    await update.message.reply_document(open(file_path, "rb"), filename=f"{query}.mp3")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /info <song name>")
        return
    query = " ".join(context.args)
    song_info = await get_info(query)
    if not song_info:
        await update.message.reply_text("❌ Song info not found.")
        return
    text = f"🎵 **{song_info['title']}**\n💽 Artist: {song_info['artist']}\n⏱ Duration: {song_info['duration']}\n🔗 URL: {song_info['url']}"
    await update.message.reply_text(text, parse_mode=None)
