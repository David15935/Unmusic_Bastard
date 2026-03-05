# Unmusic_Bastard Telegram Music Bot

Telegram music bot for searching, playing, downloading, lyrics, trending songs, queue, playlists, resume uploads, and inline search.

## Latest Commit
- Commit: `5955e26`
- Message: `fix_inline_help_jsruntime`
- Includes:
- Fixed inline search flow and result payload
- Added `/help` with detailed examples
- Fixed `yt-dlp` `js_runtimes` format error

## Features
- MP3 delivery from YouTube search/url
- `/search` with paginated buttons (Play/Queue)
- `/download` and `/play`
- `/lyrics` (Genius + fallback)
- `/info`
- `/trending`
- Queue: `/queue`, `/skip`
- Playlists: create/list/add/show/play/remove/removeitem
- `/resume` for failed/partial uploads
- Inline mode: `@your_bot_username <song or artist>`

## Commands
- `/start`
- `/help`
- `/play <song|artist|url>`
- `/search <song|artist>`
- `/download <song|artist|url>`
- `/lyrics <song and artist>`
- `/info <song|artist|url>`
- `/trending`
- `/queue`
- `/skip`
- `/playlist <subcommand>`
- `/resume`

## Project Structure
```text
Unmusic_Bastard/
  bot/
    main.py
    handlers.py
    player.py
    lyrics.py
    trending.py
    queue.py
  downloads/
  covers/
  logs/
  .env
  requirements.txt
  docker-compose.yml
```

## Install
1. Clone repo:
```bash
git clone https://github.com/David15935/Unmusic_Bastard.git
cd Unmusic_Bastard
```

2. Create venv and install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Install FFmpeg (Windows):
```powershell
winget install --id Gyan.FFmpeg -e --source winget --accept-source-agreements --accept-package-agreements
```

4. Install Node.js (recommended for yt-dlp JS extraction):
```powershell
winget install -e --id OpenJS.NodeJS.LTS --source winget --accept-source-agreements --accept-package-agreements
```

5. Create `.env`:
```env
BOT_TOKEN=your_telegram_bot_token
GENIUS_TOKEN=your_genius_api_token
```

## Run
```powershell
.venv\Scripts\python -m bot.main
```

## How To Use
1. Open bot chat and run:
```text
/start
/help
```

2. Quick examples:
```text
/play burna boy last last
/search adele hello
/download https://www.youtube.com/watch?v=dQw4w9WgXcQ
/lyrics love nwantiti ckay
/info calm down rema
/trending
```

3. Inline mode usage:
- Enable inline mode in BotFather (`/setinline`)
- In any chat type:
```text
@your_bot_username asake lonely at the top
```

4. If upload breaks on long file:
```text
/resume
```

## Optional: Local Telegram Bot API (for larger upload capability)
1. Install Docker Desktop.
2. Configure `local-bot-api.env` from `local-bot-api.env.example`.
3. Start:
```bash
docker compose up -d
```
4. Add to `.env`:
```env
LOCAL_BOT_API_URL=http://localhost:8081/bot
LOCAL_BOT_API_FILE_URL=http://localhost:8081/file/bot
```

## Notes
- Telegram cloud Bot API has upload limits per file.
- This bot can split large files and send in parts.
- For very high concurrency, use VPS + webhook + queue workers.

