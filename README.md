# Telegram Philosophy Poll Bot

An intelligent, persistent Telegram bot built to manage scheduling and act as an AI assistant for the Philadelphia Philosophy Circle.

## Features
- **Smart Polls:** Automatically asks for the meeting day (Tuesday) and time (Thursday), carrying over the winning day's context automatically.
- **Conflict Resolution & Reminders:** Automatically pings users who haven't voted yet, and tags users who voted for the "losing" day to ask if they can flex their schedule.
- **Silent User Discovery:** Automatically learns who is in the group by listening to messages and mentions. No `/join` commands needed!
- **AI Assistant:** Powered by Google Gemini. Mention the bot to ask questions about the curriculum or log completed meetings via natural language.

## Prerequisites
- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Gemini API Key

## Local Setup

1. **Clone and Install:**
   ```sh
   git clone git@github.com:san9zubr/poll-creation-tg-bot.git
   cd poll-creation-tg-bot
   uv sync
   ```

2. **Configuration (`.env`):**
   Create a `.env` file in the root directory:
   ```env
   BOT_TOKEN="your-telegram-bot-token"
   CHAT_ID="-100123456789"
   GEMINI_API_KEY="your-gemini-api-key"
   ```

3. **Curriculum Setup:**
   Paste the contents of your Google Doc schedule into a file named `curriculum.txt` in the root directory. The bot uses this to answer questions.

4. **Run Locally:**
   ```sh
   uv run python bot.py
   ```

## Deploying to a VPS (systemd)

Since this bot needs to run persistently to listen for votes and messages, a VPS is highly recommended. You can run it easily using `systemd`.

1. Clone the repo and set up the `.env` and `curriculum.txt` files on your server as shown above.
2. Create a service file:
   ```sh
   sudo nano /etc/systemd/system/philosophybot.service
   ```
3. Add the following configuration (replace `/path/to/bot` and `user` with your actual paths):
   ```ini
   [Unit]
   Description=Philosophy Telegram Bot
   After=network.target

   [Service]
   User=your_linux_user
   WorkingDirectory=/path/to/bot/poll-creation-tg-bot
   ExecStart=/path/to/bot/poll-creation-tg-bot/.venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
4. Start and enable the service:
   ```sh
   sudo systemctl daemon-reload
   sudo systemctl enable philosophybot
   sudo systemctl start philosophybot
   ```
5. Check logs:
   ```sh
   sudo journalctl -u philosophybot -f
   ```
