# 🌸 Yuki Bot

> *Your AI Girlfriend & Group Chat Bestie* — An advanced Telegram chatbot that keeps GCs alive, sends gifts, learns stickers, tags everyone, generates quote stickers, and replies like a real human~ 💗

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 AI Replies | GPT-powered girlfriend-mode responses |
| 💬 Smart Memory | Learns from chats, saves replies & stickers |
| 🎀 Sticker Learning | Auto-saves & replies with community stickers |
| 🎁 Gift System | Send 12+ cute gifts to friends |
| 📢 @all Tagging | Tag everyone in GC via Telethon |
| ✨ Quote Stickers | Turn messages into beautiful stickers |
| 🌙 GC Revival | Auto-revives silent groups |
| 🏆 Leaderboard | Track most active members |
| 📊 Stats | Global bot statistics |
| 🔧 Maintenance | Toggle maintenance mode |
| 📡 Broadcast | Send messages to all users |
| 👑 Owner Panel | Beautiful owner dashboard |

---

## 📁 Project Structure

```
Yuki/                      ← Root folder
├── __main__.py            ← Entry point (python -m yuki)
├── config.py              ← Root config re-export
├── requirements.txt
├── Procfile               ← Heroku/Railway deploy
├── runtime.txt            ← Python 3.11
├── setup.sh               ← Quick setup script
├── .env.example           ← Environment template
├── LICENSE
│
└── yuki/                  ← Main package
    ├── core/
    │   ├── config.py      ← All settings & env vars
    │   ├── database.py    ← MongoDB operations (motor)
    │   └── logger.py      ← Colored logging + Telegram relay
    │
    ├── handlers/
    │   ├── start.py       ← /start — beautiful UI
    │   ├── help.py        ← /help — 4-page paginated
    │   ├── ping.py        ← /ping /health
    │   ├── chat.py        ← AI replies, sticker learning
    │   ├── gifts.py       ← /gift /mygift system
    │   ├── admin.py       ← /stats /active /me /broadcast etc.
    │   └── callbacks.py   ← Back/cancel/misc callbacks
    │
    ├── plugins/
    │   ├── tagall.py      ← @all @tagall (Telethon)
    │   ├── quote.py       ← /qt /quote stickers
    │   └── revival.py     ← Auto GC revival scheduler
    │
    ├── utils/
    │   ├── locale.py      ← YAML string loader
    │   ├── keyboards.py   ← All InlineKeyboard layouts
    │   ├── helpers.py     ← Decorators & utilities
    │   └── brain.py       ← AI chat module
    │
    └── locals/
        └── en.yml         ← All text strings (English)
```

---

## 🚀 Quick Setup

### 1. Clone & Setup
```bash
git clone https://github.com/youruser/yuki-bot
cd yuki-bot
chmod +x setup.sh && ./setup.sh
```

### 2. Configure
```bash
cp .env.example .env
nano .env  # Fill in your values
```

### 3. Run
```bash
source venv/bin/activate
python -m yuki
```

---

## ⚙️ Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | BotFather token |
| `OWNER_ID` | ✅ | Your Telegram user ID |
| `MONGO_URI` | ✅ | MongoDB connection string |
| `MONGO_DB_NAME` | ✅ | Database name (default: `yukidb`) |

### Optional (but recommended)
| Variable | Description |
|----------|-------------|
| `AI_API_KEY` | OpenAI key for smart replies |
| `API_ID` + `API_HASH` + `SESSION_STRING` | Telethon for @all tagging |
| `LOG_GROUP_ID` | Group to forward error logs |
| `SUPPORT_LINK` | Support group link |
| `UPDATES_CHANNEL` | Updates channel link |

---

## 📋 Commands

### Basic
| Command | Description |
|---------|-------------|
| `/start` | Launch Yuki |
| `/help` | Paginated help menu |
| `/ping` | Check latency |
| `/health` | System status |
| `/me` | Your profile & gifts |
| `/stats` | Global stats |

### Social
| Command | Description |
|---------|-------------|
| `/gift` | Send a gift (reply to user) |
| `/mygift` | View your gift collection |
| `/qt` or `/quote` | Quote sticker (reply to message) |
| `@all` / `@tagall` | Tag all members (admin) |
| `/leaderboard` | Top active users |

### Admin / Owner
| Command | Description |
|---------|-------------|
| `/active` | Active users list (admin) |
| `/broadcast` | Message all users (owner) |
| `/maintenance` | Toggle maintenance mode (owner) |

---

## 🌙 GC Revival

Yuki automatically sends a revival message when a group is silent for too long.

Configure in `.env`:
```env
AUTO_REVIVE_ENABLED=true
AUTO_REVIVE_MINUTES=30
```

---

## ☁️ Deploy

### Railway / Heroku
1. Connect your GitHub repo
2. Add environment variables
3. Deploy — Procfile handles the rest

### VPS (systemd)
```ini
[Unit]
Description=Yuki Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/yuki-bot
ExecStart=/home/ubuntu/yuki-bot/venv/bin/python -m yuki
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 💗 Credits

Developed with love by **DUGGU**  
Inspired by **Yumeko Jabami** from *Kakegurui* 🎴

---

*Yuki Bot — she's always there for you~ ✨*
