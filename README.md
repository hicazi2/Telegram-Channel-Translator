# Telegram Channel Translator 🚌

A bot that automatically translates GTT Torino's public transport alerts from Italian to English and forwards them to a Telegram group chat in real time.

## The Problem
GTT (Gruppo Torinese Trasporti) publishes service alerts — line diversions, metro suspensions, delays — only in Italian. Non-Italian speakers just like me who is a student living in or visiting Turin have no way to stay informed about disruptions affecting their commute unless they choose to translate each message one by one manually.

## The Solution
This bot monitors GTT's official RSS feed every minute. When a new alert is detected, it translates it from Italian to English using Google Translate and forwards both the original and translated versions to a Telegram group.

## How It Works
1. Polls GTT's RSS feed every minute
2. Detects new entries using MD5 hashing to avoid duplicates
3. Translates Italian text to English via deep-translator
4. Sends a formatted bilingual message to a Telegram group via Bot API

## Tech Stack
- **Python 3** — core language
- **python-telegram-bot** — Telegram Bot API
- **deep-translator** — free Google Translate wrapper
- **feedparser** — RSS feed parsing
- **Railway** — cloud deployment (free tier)

## Setup

### Prerequisites
- Python 3.8+
- A Telegram account
- A Telegram Bot token from @BotFather

### Getting Your Credentials
- **BOT_TOKEN**: Open Telegram, search for @BotFather, send `/newbot` and follow the steps
- **GROUP_ID**: Add @userinfobot to your group — it will automatically send you the group ID (a negative number like `-1001234567890`)

### Running Locally

1. Clone the repo:

        git clone https://github.com/hicazi2/Telegram-Channel-Translator.git

2. Create a `.env` file in the root folder:

        BOT_TOKEN=your_telegram_bot_token
        GROUP_ID=your_telegram_group_id

3. Install dependencies:

        pip install -r requirements.txt

4. Run:

        python main.py

### Deploying to Railway (recommended for 24/7 uptime when your computer is not available)

1. Fork this repo to your GitHub account
2. Go to [railway.app](https://railway.app) and sign up with GitHub
3. Click **New Project** → **Deploy from GitHub repo** → select your fork
4. Go to the **Variables** tab and add `BOT_TOKEN` and `GROUP_ID`
5. Railway will build and deploy automatically — your bot will be online within minutes

## Why I Built This
I use Turin's public transport daily and found it frustrating that disruption alerts were only available in Italian. I built this to solve a real problem for myself and other non-Italian speakers in the city.