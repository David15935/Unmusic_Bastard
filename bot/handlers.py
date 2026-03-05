import asyncio
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import ContextTypes

from bot.player import fetch_audio, get_info, search_youtube, split_audio_for_telegram
from bot.lyrics import fetch_lyrics
from bot.trending import get_trending
from bot.queue import (
    add_song,
    next_song,
    list_queue,
    create_playlist,
    list_playlists,
    add_to_playlist,
    get_playlist,
    remove_playlist,
    remove_from_playlist,
)

logger = logging.getLogger(__name__)

SEARCH_PAGE_SIZE = 5
DOWNLOAD_TIMEOUT_SEC = 1800
UPLOAD_TIMEOUT_SEC = 900
MAX_CONCURRENT_DOWNLOADS = 6

_download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)


def _is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def _format_result(result, index):
    title = result.get("title") or "Unknown"
    uploader = result.get("uploader") or "Unknown"
    duration = result.get("duration") or "?"
    return f"{index}. {title} | {uploader} | {duration}s"


def _create_task(context: ContextTypes.DEFAULT_TYPE, coro):
    task = context.application.create_task(coro)

    def _done(t):
        try:
            t.result()
        except Exception:
            logger.exception("Background task failed")

    task.add_done_callback(_done)
    return task


async def _send_part_with_retry(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    part_path: str,
    title: str,
    filename: str,
) -> str:
    last_error = None

    for attempt in range(1, 4):
        try:
            with open(part_path, "rb") as f:
                input_file = InputFile(f, filename=filename)
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=input_file,
                    title=title,
                    write_timeout=300,
                    read_timeout=300,
                    connect_timeout=30,
                    pool_timeout=30,
                )
            return "audio"
        except (TimedOut, NetworkError) as exc:
            last_error = exc
            logger.warning("Audio upload retry %s failed for %s: %s", attempt, part_path, exc)
            await asyncio.sleep(attempt * 2)

    for attempt in range(1, 3):
        try:
            with open(part_path, "rb") as f:
                input_file = InputFile(f, filename=filename)
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=input_file,
                    write_timeout=300,
                    read_timeout=300,
                    connect_timeout=30,
                    pool_timeout=30,
                )
            return "document"
        except (TimedOut, NetworkError) as exc:
            last_error = exc
            logger.warning(
                "Document upload retry %s failed for %s: %s", attempt, part_path, exc
            )
            await asyncio.sleep(attempt * 2)

    raise RuntimeError(f"Upload failed after retries: {last_error}")


async def _send_parts(
    context: ContextTypes.DEFAULT_TYPE,
    message,
    chat_id: int,
    title: str,
    parts,
    start_idx: int = 0,
    progress_state: dict | None = None,
) -> None:
    if len(parts) > 1 and start_idx == 0:
        await message.reply_text(f"Large file detected. Sending {len(parts)} parts...")

    for idx in range(start_idx, len(parts)):
        part = parts[idx]
        size = os.path.getsize(part)
        human_idx = idx + 1
        logger.info("Uploading part=%s size=%s bytes path=%s", human_idx, size, part)
        await message.reply_text(
            f"Uploading part {human_idx}/{len(parts)} ({round(size/1024/1024,1)} MB)..."
        )
        filename = f"{title}_part{human_idx}{os.path.splitext(part)[1]}"
        sent_as = await _send_part_with_retry(
            context=context,
            chat_id=chat_id,
            part_path=part,
            title=title if len(parts) == 1 else f"{title} (Part {human_idx})",
            filename=filename,
        )
        logger.info("Uploaded part=%s as=%s", human_idx, sent_as)
        if progress_state is not None:
            progress_state["next_idx"] = human_idx


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.warning("Ignored Telegram conflict: %s", context.error)
        return
    logger.exception("Unhandled exception", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("Something went wrong.")

async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = update.to_dict()
    except Exception:
        data = str(update)
    logger.info("update=%s", data)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("/start from chat_id=%s", update.effective_chat.id if update.effective_chat else None)
    text = (
        "Music Bot ready.\n\n"
        "Commands:\n"
        "/play <song>\n"
        "/download <song>\n"
        "/lyrics <song>\n"
        "/info <song>\n"
        "/trending\n"
        "/queue\n"
        "/skip\n"
        "/playlist <subcommand>\n"
        "/resume - Resume failed upload\n"
    )
    await update.effective_message.reply_text(text)


async def _send_search_page(message, context: ContextTypes.DEFAULT_TYPE, page: int):
    results = context.chat_data.get("search_results", [])
    query = context.chat_data.get("search_query", "")
    total = len(results)
    if total == 0:
        await message.reply_text("No results found.")
        return

    start = page * SEARCH_PAGE_SIZE
    end = start + SEARCH_PAGE_SIZE
    page_results = results[start:end]

    lines = [f"Results for: {query}"]
    for idx, r in enumerate(page_results, start=start + 1):
        lines.append(_format_result(r, idx))

    result_map = context.chat_data.setdefault("result_map", {})
    for r in page_results:
        if r.get("id"):
            result_map[r["id"]] = r

    keyboard = []
    for r in page_results:
        rid = r.get("id")
        if not rid:
            continue
        keyboard.append(
            [
                InlineKeyboardButton("Play", callback_data=f"play|{rid}"),
                InlineKeyboardButton("Queue", callback_data=f"queue|{rid}"),
            ]
        )

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("Prev", callback_data=f"page|{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton("Next", callback_data=f"page|{page + 1}"))
    if nav:
        keyboard.append(nav)

    markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("\n".join(lines), reply_markup=markup)


async def _play_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    message = update.effective_message or (update.callback_query.message if update.callback_query else None)
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not message or not chat_id:
        return

    logger.info("Preparing download for query=%s", query)
    await message.reply_text("Preparing audio...")

    try:
        async with _download_semaphore:
            data = await asyncio.wait_for(fetch_audio(query), timeout=DOWNLOAD_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        await message.reply_text("Download timed out. Try another result.")
        return
    except Exception as exc:
        await message.reply_text(f"Download failed: {exc}")
        return

    path = data.get("path")
    logger.info("Downloaded file path=%s", path)
    title = data.get("title") or "audio"
    if not path:
        await message.reply_text("Download failed.")
        return

    try:
        parts = await split_audio_for_telegram(path)
        progress_state = {"parts": parts, "title": title, "next_idx": 0}
        context.chat_data["resume_upload"] = progress_state
        await _send_parts(
            context,
            message,
            chat_id,
            title,
            parts,
            start_idx=0,
            progress_state=progress_state,
        )
        context.chat_data.pop("resume_upload", None)
        await message.reply_text("Sent.")
    except asyncio.TimeoutError:
        if "parts" not in locals():
            context.chat_data["resume_upload"] = {"parts": [], "title": title, "next_idx": 0}
        await message.reply_text("Upload timed out. Use /resume to continue from last part.")
    except Exception as exc:
        logger.exception("Upload failed")
        await message.reply_text(f"Upload failed: {exc}")


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("/play args=%s chat_id=%s", context.args, update.effective_chat.id if update.effective_chat else None)
    if not context.args:
        await update.effective_message.reply_text("Usage: /play <song name>")
        return

    query = " ".join(context.args).strip()
    if _is_url(query):
        _create_task(context, _play_and_send(update, context, query))
        return

    results = await search_youtube(query, limit=15)
    if not results:
        await update.effective_message.reply_text("No results found.")
        return

    context.chat_data["search_results"] = results
    context.chat_data["search_query"] = query
    await _send_search_page(update.effective_message, context, page=0)


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("/download args=%s chat_id=%s", context.args, update.effective_chat.id if update.effective_chat else None)
    if not context.args:
        await update.effective_message.reply_text("Usage: /download <song name>")
        return

    query = " ".join(context.args).strip()
    await update.effective_message.reply_text("Preparing download...")

    try:
        async with _download_semaphore:
            data = await asyncio.wait_for(fetch_audio(query), timeout=DOWNLOAD_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        await update.effective_message.reply_text("Download timed out. Try another result.")
        return
    except Exception as exc:
        await update.effective_message.reply_text(f"Download failed: {exc}")
        return

    path = data.get("path")
    logger.info("Downloaded file path=%s", path)
    title = data.get("title") or "audio"
    if not path:
        await update.effective_message.reply_text("Download failed.")
        return

    try:
        parts = await split_audio_for_telegram(path)
        progress_state = {"parts": parts, "title": title, "next_idx": 0}
        context.chat_data["resume_upload"] = progress_state
        await _send_parts(
            context=context,
            message=update.effective_message,
            chat_id=update.effective_chat.id,
            title=title,
            parts=parts,
            start_idx=0,
            progress_state=progress_state,
        )
        context.chat_data.pop("resume_upload", None)
        await update.effective_message.reply_text("Sent.")
    except Exception as exc:
        logger.exception("Download command upload failed")
        await update.effective_message.reply_text(
            f"Upload failed: {exc}. Use /resume to continue."
        )


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.chat_data.get("resume_upload")
    if not state:
        await update.effective_message.reply_text("No pending upload to resume.")
        return

    parts = state.get("parts") or []
    title = state.get("title") or "audio"
    next_idx = int(state.get("next_idx", 0))

    if not parts or next_idx >= len(parts):
        context.chat_data.pop("resume_upload", None)
        await update.effective_message.reply_text("Nothing left to resume.")
        return

    try:
        await _send_parts(
            context=context,
            message=update.effective_message,
            chat_id=update.effective_chat.id,
            title=title,
            parts=parts,
            start_idx=next_idx,
            progress_state=state,
        )
        context.chat_data.pop("resume_upload", None)
        await update.effective_message.reply_text("Resume completed.")
    except Exception as exc:
        logger.exception("Resume failed")
        await update.effective_message.reply_text(f"Resume failed: {exc}")


async def lyrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Usage: /lyrics <song name>")
        return

    query = " ".join(context.args).strip()
    text = fetch_lyrics(query)

    chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await update.effective_message.reply_text(chunk)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Usage: /info <song name>")
        return

    query = " ".join(context.args).strip()
    details = await get_info(query)
    if not details:
        await update.effective_message.reply_text("No info found.")
        return

    await update.effective_message.reply_text(details)


async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("/trending chat_id=%s", update.effective_chat.id if update.effective_chat else None)
    try:
        items = get_trending(limit=10)
    except Exception:
        await update.effective_message.reply_text("Trending is unavailable right now.")
        return

    context.chat_data["trending_results"] = items
    buttons = [
        [InlineKeyboardButton(item, callback_data=f"trend|{idx}")]
        for idx, item in enumerate(items)
    ]
    await update.effective_message.reply_text(
        "Trending songs:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("button data=%s chat_id=%s", update.callback_query.data if update.callback_query else None, update.effective_chat.id if update.effective_chat else None)
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data.startswith("page|"):
        page = int(data.split("|", 1)[1])
        await _send_search_page(query.message, context, page)
        return

    if data.startswith("play|"):
        await query.message.reply_text("Downloading...")
        rid = data.split("|", 1)[1]
        result_map = context.chat_data.get("result_map", {})
        item = result_map.get(rid)
        if not item:
            await query.message.reply_text("Result not found.")
            return
        _create_task(context, _play_and_send(update, context, item.get("webpage_url") or item.get("url")))
        return

    if data.startswith("queue|"):
        rid = data.split("|", 1)[1]
        result_map = context.chat_data.get("result_map", {})
        item = result_map.get(rid)
        if not item:
            await query.message.reply_text("Result not found.")
            return
        add_song(update.effective_chat.id, item.get("webpage_url") or item.get("url"))
        await query.message.reply_text("Added to queue.")
        return

    if data.startswith("trend|"):
        await query.message.reply_text("Downloading...")
        idx = int(data.split("|", 1)[1])
        items = context.chat_data.get("trending_results", [])
        if idx >= len(items):
            await query.message.reply_text("Item not found.")
            return
        _create_task(context, _play_and_send(update, context, items[idx]))
        return


async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = list_queue(update.effective_chat.id)
    if not q:
        await update.effective_message.reply_text("Queue is empty.")
        return

    lines = [f"{idx + 1}. {item}" for idx, item in enumerate(q)]
    await update.effective_message.reply_text("\n".join(lines))


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    song = next_song(update.effective_chat.id)
    if not song:
        await update.effective_message.reply_text("Queue is empty.")
        return
    _create_task(context, _play_and_send(update, context, song))


async def playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /playlist create|list|show|add|play|remove|removeitem"
        )
        return

    cmd = context.args[0].lower()
    args = context.args[1:]
    chat_id = update.effective_chat.id

    if cmd == "create":
        name = " ".join(args).strip()
        if not name:
            await update.effective_message.reply_text("Usage: /playlist create <name>")
            return
        ok = create_playlist(chat_id, name)
        await update.effective_message.reply_text("Created." if ok else "Already exists.")
        return

    if cmd == "list":
        names = list_playlists(chat_id)
        await update.effective_message.reply_text("\n".join(names) if names else "No playlists.")
        return

    if cmd == "show":
        name = " ".join(args).strip()
        items = get_playlist(chat_id, name)
        if items is None:
            await update.effective_message.reply_text("Playlist not found.")
            return
        if not items:
            await update.effective_message.reply_text("Playlist is empty.")
            return
        lines = [f"{idx + 1}. {item}" for idx, item in enumerate(items)]
        await update.effective_message.reply_text("\n".join(lines))
        return

    if cmd == "add":
        if len(args) < 2:
            await update.effective_message.reply_text("Usage: /playlist add <name> <song>")
            return
        name = args[0]
        item = " ".join(args[1:])
        ok = add_to_playlist(chat_id, name, item)
        await update.effective_message.reply_text("Added." if ok else "Playlist not found.")
        return

    if cmd == "play":
        name = " ".join(args).strip()
        items = get_playlist(chat_id, name)
        if items is None:
            await update.effective_message.reply_text("Playlist not found.")
            return
        if not items:
            await update.effective_message.reply_text("Playlist is empty.")
            return
        for item in items:
            add_song(chat_id, item)
        await update.effective_message.reply_text(f"Queued {len(items)} songs.")
        return

    if cmd == "remove":
        name = " ".join(args).strip()
        ok = remove_playlist(chat_id, name)
        await update.effective_message.reply_text("Removed." if ok else "Playlist not found.")
        return

    if cmd == "removeitem":
        if len(args) < 2:
            await update.effective_message.reply_text(
                "Usage: /playlist removeitem <name> <index>"
            )
            return
        name = args[0]
        try:
            index = int(args[1]) - 1
        except ValueError:
            await update.effective_message.reply_text("Index must be a number.")
            return
        ok = remove_from_playlist(chat_id, name, index)
        await update.effective_message.reply_text("Removed." if ok else "Item not found.")
        return

    await update.effective_message.reply_text("Unknown subcommand.")
