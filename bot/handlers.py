# bot/handlers.py
import logging
from telegram import (
    Update, InlineQueryResultArticle, InputTextMessageContent
)
from telegram.ext import ContextTypes
from bot.music_api import (
    search_youtube, download_audio, get_info, get_trending, get_lyrics_basic
)
from bot.queue_manager import (
    add_song_to_queue, get_queue, clear_queue, skip_current, pause_queue, resume_queue
)
from bot.utils import escape_md, mk_buttons

logger = logging.getLogger(__name__)

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🎵 Music Bot ready.\n\n"
        "Commands:\n"
        "/play <song> - search & play (queues)\n"
        "/download <song> - download mp3\n"
        "/lyrics <song> - get lyrics\n"
        "/info <song> - metadata\n"
        "/queue - show chat queue\n"
        "/skip - skip current\n"
        "/pause - pause queue\n"
        "/resume - resume queue\n"
        "/stop - clear queue\n\n"
        "Inline: type @YourBotName <song>"
    )
    await update.message.reply_text(txt)

# ---------- /search (useful for chat searches) ----------
async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <song or artist>")
        return
    query = " ".join(context.args)
    results = await search_youtube(query, limit=5, offset=0)
    if not results:
        await update.message.reply_text("No results.")
        return
    lines = []
    buttons = []
    for r in results:
        lines.append(f"{r['title']} ({r.get('duration','?')}s)")
        # callback will be "play:<url_id>" but to avoid pass raw urls we pass webpage_url
        buttons.append([(f"Play", f"play:{r['webpage_url']}"), ("Download", f"dl:{r['webpage_url']}")])
    await update.message.reply_text("\n".join(lines), reply_markup=mk_buttons(buttons))

# ---------- /play ----------
async def play_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /play <song name>")
        return
    query = " ".join(context.args)
    results = await search_youtube(query, limit=1)
    if not results:
        await update.message.reply_text("No results found.")
        return
    r = results[0]
    # download and add to queue
    await update.message.reply_text(f"Downloading {r['title']} ...")
    file_path = await download_audio(r['webpage_url'])
    song = {"title": r['title'], "file": file_path, "meta": r}
    await add_song_to_queue(update.effective_chat.id, song, context)
    await update.message.reply_text(f"Queued: {r['title']}")

# ---------- /download ----------
async def download_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /download <song name>")
        return
    query = " ".join(context.args)
    results = await search_youtube(query, limit=1)
    if not results:
        await update.message.reply_text("No results found.")
        return
    r = results[0]
    await update.message.reply_text(f"Downloading {r['title']} ...")
    path = await download_audio(r['webpage_url'])
    try:
        await update.message.reply_document(document=open(path, "rb"), filename=f"{escape_md(r['title'])}.mp3")
    except Exception as e:
        await update.message.reply_text(f"Failed to send file: {e}")

# ---------- /lyrics ----------
async def lyrics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lyrics <artist - title> or <title>")
        return
    query = " ".join(context.args)
    lyrics = await get_lyrics_basic(query)
    await update.message.reply_text(lyrics[:4000])

# ---------- /info ----------
async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /info <song name>")
        return
    query = " ".join(context.args)
    results = await search_youtube(query, limit=1)
    if not results:
        await update.message.reply_text("No results found.")
        return
    r = results[0]
    info = await get_info(r['webpage_url'])
    txt = f"Title: {info.get('title')}\nURL: {info.get('webpage_url')}\nDuration: {info.get('duration')} sec"
    await update.message.reply_text(txt)

# ---------- /queue ----------
async def queue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = get_queue(update.effective_chat.id)
    if not q:
        await update.message.reply_text("Queue is empty.")
        return
    text = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(q)])
    await update.message.reply_text(f"🎵 Queue:\n{text}")

# ---------- /skip ----------
async def skip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    skip_current(update.effective_chat.id)
    # restart player if items remain
    if get_queue(update.effective_chat.id):
        # resume player
        await update.message.reply_text("Skipped. Moving to next song if available.")
        # start new player if needed
        # resume handled automatically by queue_manager when skip cancels and add rest
    else:
        await update.message.reply_text("Queue cleared or nothing to play.")

# ---------- /pause ----------
async def pause_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pause_queue(update.effective_chat.id)
    await update.message.reply_text("Playback paused. Use /resume to continue.")

# ---------- /resume ----------
async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resume_queue(update.effective_chat.id, context)
    await update.message.reply_text("Playback resumed.")

# ---------- /stop ----------
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_queue(update.effective_chat.id)
    await update.message.reply_text("Queue cleared.")

# ---------- /trending ----------
async def trending_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = await get_trending(limit=8)
    if not items:
        await update.message.reply_text("No trending results available.")
        return
    lines = [f"{i+1}. {it['title']}" for i, it in enumerate(items)]
    await update.message.reply_text("🔥 Trending:\n" + "\n".join(lines))

# ---------- INLINE SEARCH (using offset pagination) ----------
async def inline_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    offset = int(update.inline_query.offset or 0)
    limit = 5
    results = await search_youtube(query, limit=limit, offset=offset)
    items = []
    next_offset = offset + limit if len(results) == limit else ""
    for r in results:
        items.append(
            InlineQueryResultArticle(
                id=r['id'],
                title=r['title'],
                input_message_content=InputTextMessageContent(f"/play {r['title']}"),
                description=f"Duration: {r.get('duration','?')}s"
            )
        )
    await update.inline_query.answer(items, cache_time=30, is_personal=True, next_offset=str(next_offset))
