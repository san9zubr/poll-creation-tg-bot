# Telegram Poll Bot

A small CLI tool for sending polls to a Telegram group chat. Used to coordinate meetup days and times.

## Setup

1. Clone the repo:
   ```sh
   git clone git@github.com:san9zubr/poll-creation-tg-bot.git
   cd poll-creation-tg-bot
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Create a Telegram bot via [@BotFather](https://t.me/BotFather) and get the bot token.
4. Add the bot to your group chat.
5. Find your chat ID by running the helper script (see below).
6. Set environment variables:
   ```sh
   export BOT_TOKEN="your-bot-token"
   export CHAT_ID="your-chat-id"
   ```

### Finding your chat ID

```sh
python get_chat_id.py
```

Send any message in the group — the script will print the chat ID to the console.

## Usage

Send a poll to choose a meetup **day** (nearest Saturday/Sunday):

```sh
python send_poll.py --poll choose_day
```

Send a poll to choose a meetup **time** (12pm–7pm):

```sh
python send_poll.py --poll choose_time
```

Polls are non-anonymous and allow multiple answers.

## Dependencies

- Python 3.9+
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 20.6
