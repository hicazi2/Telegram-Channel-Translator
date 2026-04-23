# Telegram Channel Translator 🚌

A bot that automatically translates GTT Torino's public transport alerts from Italian to English and forwards them to a Telegram group in real time.

## The Problem
GTT (Gruppo Torinese Trasporti) publishes service alerts — line diversions, metro suspensions, delays — only in Italian, exclusively on their Telegram channel [@gttavvisi](https://t.me/gttavvisi). Non-Italian speakers living in or visiting Turin have no way to stay informed about disruptions affecting their commute.

## The Solution
This bot reads messages from @gttavvisi as a channel member, translates them from Italian to English, and forwards both the original and translated versions to a Telegram group — automatically, every 5 minutes, for free.

## How It Works
1. [cron-job.org](https://cron-job.org) triggers the GitHub Actions workflow every 5 minutes via a repository dispatch webhook
2. Connects to Telegram using a Telethon user session and reads the latest messages from @gttavvisi
3. Skips already-seen messages using a persistent ID cache (GitHub Actions Cache)
4. Translates new messages from Italian to English via Azure Translator API
5. Sends a formatted bilingual message to a Telegram group via Bot API

## Tech Stack
- **Python 3** — core language
- **Telethon** — reads messages from the GTT channel as a Telegram user
- **python-telegram-bot** — sends translated messages to the group via Bot API
- **Azure Translator API** — translation (2M characters/month free tier)
- **GitHub Actions** — runs the bot on each trigger
- **cron-job.org** — triggers the workflow reliably every 5 minutes (free)

## Setup

### Prerequisites
- Python 3.8+
- A Telegram account (must be a member of @gttavvisi)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)
- A Telegram Bot token from @BotFather
- An Azure account with a Translator resource (free tier: 2M chars/month)
- A [cron-job.org](https://cron-job.org) account (free)

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
   - `AZURE_TRANSLATOR_KEY` — your Azure Translator API key
   - `AZURE_TRANSLATOR_REGION` — your Azure resource region (e.g. `eastus`)
3. Go to **Actions → Poll GTT Channel → Run workflow** to trigger the first run

The first run sends the latest GTT message as a startup test so you can verify everything works.

### 4. Set Up cron-job.org

The workflow is triggered externally by [cron-job.org](https://cron-job.org) every 5 minutes — this is more reliable than GitHub's built-in schedule trigger, which can delay runs by hours.

1. Create a free account at [cron-job.org](https://cron-job.org)
2. Create a new cronjob with these settings:
   - **URL:** `https://api.github.com/repos/YOUR_USERNAME/Telegram-Channel-Translator/dispatches`
   - **Schedule:** Every 5 minutes
   - **Request method:** POST
   - **Headers:**
     - `Authorization`: `Bearer YOUR_GITHUB_PAT` (classic PAT with `workflow` scope)
     - `Accept`: `application/vnd.github+json`
     - `Content-Type`: `application/json`
   - **Body:** `{"event_type":"poll"}`
3. Save and do a test run — you should see a new workflow run appear in GitHub Actions within seconds

### Running Locally

Create a `.env` file:

```
API_ID=your_api_id
API_HASH=your_api_hash
SESSION_STRING=your_session_string
BOT_TOKEN=your_bot_token
GROUP_ID=your_group_id
AZURE_TRANSLATOR_KEY=your_azure_key
AZURE_TRANSLATOR_REGION=your_azure_region
```

Then:

```bash
pip install -r requirements.txt
python main.py
```

## Important Notes
- **Session security**: Keep your `SESSION_STRING` private. It gives access to your Telegram account.
- **GitHub PAT**: The classic PAT used by cron-job.org should have only the `workflow` scope. Rotate it annually when it expires.

## Why I Built This
I use Turin's public transport daily and found it frustrating that disruption alerts were only available in Italian. I built this to solve a real problem for myself and other non-Italian speakers in the city.
