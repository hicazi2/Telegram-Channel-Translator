import os
import json
import asyncio
import feedparser
import hashlib
from pathlib import Path
from telegram import Bot
from telegram.error import RetryAfter, NetworkError, TimedOut
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

RSS_URL = "https://www.gtt.to.it/cms/avvisi-e-informazioni-di-servizio?format=feed&type=rss"
SEEN_IDS_FILE = Path(__file__).parent / "seen_ids.json"

translator = GoogleTranslator(source="it", target="en")
bot = Bot(token=BOT_TOKEN)


def load_seen_ids():
    if SEEN_IDS_FILE.exists():
        try:
            return set(json.loads(SEEN_IDS_FILE.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Could not load seen_ids from disk: {e}. Starting fresh.")
    return set()


def save_seen_ids(seen_ids):
    try:
        SEEN_IDS_FILE.write_text(json.dumps(list(seen_ids)))
    except OSError as e:
        print(f"⚠️  Could not save seen_ids to disk: {e}")


seen_ids = load_seen_ids()


def get_entry_id(entry):
    raw = entry.get("title", "") + entry.get("summary", "")
    return hashlib.md5(raw.encode()).hexdigest()


async def send_with_retry(text, max_retries=3):
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode="Markdown")
            return True
        except RetryAfter as e:
            print(f"⏳ Telegram rate limit — waiting {e.retry_after}s...")
            await asyncio.sleep(e.retry_after)
        except (NetworkError, TimedOut) as e:
            wait = 2 ** attempt
            print(f"⚠️  Telegram network error ({type(e).__name__}: {e}), retrying in {wait}s...")
            await asyncio.sleep(wait)
    print(f"❌ Failed to send message after {max_retries} attempts.")
    return False


async def check_feed():
    print("🔍 Checking GTT RSS feed...")
    feed = feedparser.parse(RSS_URL)

    if feed.bozo and not feed.entries:
        print(f"❌ Failed to parse RSS feed: {feed.bozo_exception}")
        return

    print(f"📰 Found {len(feed.entries)} entries in feed")

    for entry in feed.entries:
        entry_id = get_entry_id(entry)
        if entry_id in seen_ids:
            continue

        italian_text = entry.get("summary", entry.get("title", ""))
        if not italian_text:
            seen_ids.add(entry_id)
            save_seen_ids(seen_ids)
            continue

        try:
            translated_text = translator.translate(italian_text)
        except Exception as e:
            print(f"⚠️  Translation failed ({type(e).__name__}: {e}) — will retry next poll.")
            continue

        message = (
            f"🚌 *GTT Update*\n\n"
            f"🇮🇹 *Original:*\n{italian_text}\n\n"
            f"🇬🇧 *English:*\n{translated_text}"
        )

        sent = await send_with_retry(message)
        if sent:
            seen_ids.add(entry_id)
            save_seen_ids(seen_ids)
            print(f"✅ Sent: {translated_text[:60]}...")


async def main():
    print("🤖 GTT Translator bot started!")
    print("📡 Polling RSS feed every 5 minutes...")

    if not seen_ids:
        print("⏳ No saved state found. Loading existing feed entries silently...")
        feed = feedparser.parse(RSS_URL)
        if feed.bozo and not feed.entries:
            print(f"⚠️  Could not load initial feed: {feed.bozo_exception}")
        else:
            for entry in feed.entries:
                seen_ids.add(get_entry_id(entry))
            save_seen_ids(seen_ids)
            print(f"✅ Loaded {len(seen_ids)} existing entries. Watching for new ones...")
    else:
        print(f"✅ Resumed from saved state with {len(seen_ids)} known entries.")

    while True:
        await check_feed()
        await asyncio.sleep(300)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Bot stopped.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise
