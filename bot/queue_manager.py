# bot/queue_manager.py
import asyncio
from collections import defaultdict
from typing import Dict, List
from pathlib import Path

# per-chat queues: chat_id -> list of song dicts {title,file_path,meta}
queues: Dict[int, List[dict]] = defaultdict(list)
# per-chat play tasks
play_tasks: Dict[int, asyncio.Task] = {}
# per-chat paused flags
paused: Dict[int, bool] = defaultdict(lambda: False)

async def add_song_to_queue(chat_id: int, song: dict, context):
    """
    song: {"title":..., "file":path, "meta": {...}} 
    context: telegram handler context used to start player if necessary
    """
    queues[chat_id].append(song)
    # if there's no running player, start one
    if chat_id not in play_tasks or play_tasks[chat_id].done():
        # spawn player
        play_tasks[chat_id] = context.application.create_task(player_loop(chat_id, context))

def get_queue(chat_id: int):
    return queues.get(chat_id, []).copy()

def clear_queue(chat_id: int):
    queues[chat_id].clear()
    # cancel player
    if chat_id in play_tasks and not play_tasks[chat_id].done():
        play_tasks[chat_id].cancel()

def skip_current(chat_id: int):
    # remove current by cancelling player (player will move to next)
    if chat_id in play_tasks and not play_tasks[chat_id].done():
        play_tasks[chat_id].cancel()
    # then restart player if items remain
    # caller should start new player if needed

def pause_queue(chat_id: int):
    paused[chat_id] = True

def resume_queue(chat_id: int, context):
    paused[chat_id] = False
    # if no player running, start it
    if (chat_id not in play_tasks) or play_tasks[chat_id].done():
        play_tasks[chat_id] = context.application.create_task(player_loop(chat_id, context))

async def player_loop(chat_id: int, context):
    """
    Runs in background for a specific chat, sends audio sequentially.
    Stops when queue is empty or cancelled.
    """
    try:
        while queues.get(chat_id):
            if paused.get(chat_id):
                # wait while paused
                await asyncio.sleep(1)
                continue

            song = queues[chat_id].pop(0)
            file_path = song.get("file")
            title = song.get("title", "Unknown")

            # send audio (non-blocking)
            try:
                # open file in binary
                with open(file_path, "rb") as f:
                    # send as audio so Telegram shows music UI
                    await context.bot.send_audio(chat_id=chat_id, audio=f, title=title)
            except Exception as e:
                # if sending fails, continue to next
                await context.bot.send_message(chat_id=chat_id, text=f"Failed to send {title}: {e}")

            # small wait to let Telegram process
            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        # canceled (skip or stop), exit silently
        return
    finally:
        # cleanup task entry
        if chat_id in play_tasks and play_tasks[chat_id].done():
            del play_tasks[chat_id]
