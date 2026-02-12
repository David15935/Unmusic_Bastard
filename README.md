🎵 Telegram Music Bot

A powerful Telegram music bot that lets users search, play, download MP3 files, view lyrics, manage queues, and explore trending music — all from simple text commands.

Built with Python, python-telegram-bot, yt-dlp, and Genius API.

---

🚀 Features

✅ Search songs by name ✅ Play & send MP3 directly in chat ✅ Download high‑quality audio ✅ Lyrics lookup (Genius API) ✅ Queue system (play multiple tracks) ✅ Trending music (real data) ✅ Cover art preview ✅ Cached files for faster repeat plays

---

📌 Commands

/start       – Welcome message
/search     – Search for songs
/play       – Play song by name
/download   – Download MP3
/lyrics     – Get song lyrics
/info       – Song info
/queue      – View queue
/skip       – Skip current song
/pause      – Pause playback
/resume     – Resume playback
/stop       – Stop playback
/trending   – Trending songs

---

🧱 Project Structure

music_bot/
│
├── bot/
│   ├── main.py
│   ├── handlers.py
│   ├── music_api.py
│   ├── queue_manager.py
│   ├── utils.py
│
├── requirements.txt
└── README.md

---

⚙️ Installation

1️⃣ Clone project

git clone <your-repo-url>
cd music_bot

2️⃣ Install dependencies

pip install -r requirements.txt

(Or manually)

pip install python-telegram-bot yt-dlp lyricsgenius fastapi uvicorn

---

### ⚙️ Termux Installation (Step-by-Step)

1. **Install Termux**
   Download Termux from the Play Store, F-Droid, or the official site.

2. **Update Termux packages**
   ```
   pkg update && pkg upgrade
   ```

3. **Install Python and Git**
   ```
   pkg install python git
   ```

4. **Clone the Repository**
   ```
   git clone https://github.com/David15935/Unmusic_Bastard.git
   cd Unmusic_Bastard/music_bot
   ```

5. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```
   Or install manually:
   ```
   pip install python-telegram-bot yt-dlp lyricsgenius fastapi uvicorn
   ```

6. **Set Environment Variables**
   You'll need your bot token and Genius API token.
   ```
   export BOT_TOKEN=your_telegram_bot_token
   export GENIUS_TOKEN=your_genius_api_token
   ```

7. **Run the Bot**
   ```
   python -m bot.main
   ```

---

### 🧪 Cloning & Testing on Other Platforms

1. **Clone Repository**
   ```
   git clone https://github.com/David15935/Unmusic_Bastard.git
   cd Unmusic_Bastard/music_bot
   ```

2. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Set Environment Variables**
   ```
   export BOT_TOKEN=your_telegram_bot_token
   export GENIUS_TOKEN=your_genius_api_token
   ```

4. **Run**
   ```
   python -m bot.main
   ```

---

🔐 Environment Variables

Create these variables:
BOT_TOKEN=your_telegram_bot_token
GENIUS_TOKEN=your_genius_api_token

Linux/macOS:
export BOT_TOKEN=xxx
export GENIUS_TOKEN=xxx

Windows:
set BOT_TOKEN=xxx
set GENIUS_TOKEN=xxx

---

▶️ Run Locally
python -m bot.main

---

🌍 Free Deployment (24/7)
Recommended platforms:
• Railway.app ✅ • Render.com ✅
Start command:
python -m bot.main

---

📦 Tech Stack
Python 3.10+
python-telegram-bot
yt-dlp
Genius API
FastAPI (optional uptime server)

---

⚠️ Notes
• Telegram bots send audio files (no live streaming)
• Files are cached locally for faster replays
• Works on PC, VPS, and Termux

---
📜 License
MIT License — free to use and modify.

---
⭐ Credits
Built by David Elisha Powered by Telegram, YouTube, Genius

---
Happy coding 🎧🔥