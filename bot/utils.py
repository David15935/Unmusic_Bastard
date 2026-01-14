# bot/utils.py
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def escape_md(text: str) -> str:
    if not text:
        return ""
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def mk_buttons(rows):
    """
    rows: list of lists of (text, callback_data) or (text, url) if url startswith http
    returns InlineKeyboardMarkup
    """
    out = []
    for row in rows:
        buttons = []
        for text, action in row:
            if isinstance(action, str) and action.startswith("http"):
                buttons.append(InlineKeyboardButton(text, url=action))
            else:
                buttons.append(InlineKeyboardButton(text, callback_data=action))
        out.append(buttons)
    return InlineKeyboardMarkup(out)
