# Telegram Channel Translator 🚌

A bot that automatically translates GTT Torino's public transport alerts from Italian to English and forwards them to a Telegram group in real time.

## The Problem
GTT (Gruppo Torinese Trasporti) publishes service alerts — line diversions, metro suspensions, delays — only in Italian, exclusively on their Telegram channel [@gttavvisi](https://t.me/gttavvisi). Non-Italian speakers living in or visiting Turin have no way to stay informed about disruptions affecting their commute.

## The Solution
This bot reads messages from @gttavvisi as a channel member, translates them from Italian to English, and forwards both the original and translated versions to a Telegram group — automatically, every 5 minutes, for free.

## How It Works
1. Runs every 5 minutes via GitHub Actions (free, no server needed)
2. Connects to Telegram using a Telethon user session and reads the latest messages from @gttavvisi
3. Skips already-seen messages using a persistent ID cache (GitHub Actions Cache)
4. Translates new messages from Italian to English via deep-translator
5. Sends a formatted bilingual message to a Telegram group via Bot API

## Tech Stack
- **Python 3** — core language
- **Telethon** — reads messages from the GTT channel as a Telegram user
- **python-telegram-bot** — sends translated messages to the group via Bot API
- **deep-translator** — free Google Translate wrapper
- **GitHub Actions** — free scheduled execution every 5 minutes

## Setup

### Prerequisites
- Python 3.8+
- A Telegram account (must be a member of @gttavvisi)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)
- A Telegram Bot token from @BotFather

### 1. Get Telegram API Credentials
1. Go to [my.telegram.org](https://my.telegram.org) and log in
2. Click **API development tools**
3. Create an app — you'll get an `api_id` and `api_hash`

### 2. Generate a Session String
Run this once on your local machine:

```bash
pip install telethon
python3 -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = input('API ID: ')
api_hash = input('API Hash: ')

with TelegramClient(StringSession(), int(api_id), api_hash) as client:
    print('\nYour session string:')
    print(client.session.save())
"
```

Enter your phone number and the verification code when prompted. Copy the printed session string.

### 3. Deploy with GitHub Actions

1. Fork this repo
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `API_ID` — your Telegram API id
   - `API_HASH` — your Telegram API hash
   - `SESSION_STRING` — the session string from step 2
   - `BOT_TOKEN` — your Telegram bot token
   - `GROUP_ID` — the ID of the group to send messages to (a negative number like `-1001234567890`)
3. Go to **Actions → Poll GTT Channel → Run workflow** to trigger the first run

The first run sends the latest GTT message as a startup test so you can verify everything works. From then on the workflow runs automatically every 5 minutes.

### Running Locally

Create a `.env` file:

```
API_ID=your_api_id
API_HASH=your_api_hash
SESSION_STRING=your_session_string
BOT_TOKEN=your_bot_token
GROUP_ID=your_group_id
```

Then:

```bash
pip install -r requirements.txt
python main.py
```

## Important Notes
- **60-day inactivity**: GitHub disables scheduled workflows if the repo has no commits for 60 days. GitHub emails a warning before this happens — just push any small change to reactivate.
- **Session security**: Keep your `SESSION_STRING` private. It gives access to your Telegram account.

## Why I Built This
I use Turin's public transport daily and found it frustrating that disruption alerts were only available in Italian. I built this to solve a real problem for myself and other non-Italian speakers in the city.
