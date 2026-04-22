import os
import json
import asyncio
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from telegram import Bot
from telegram.error import RetryAfter, NetworkError, TimedOut
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

CHANNEL = "gttavissi"
SEEN_IDS_FILE = Path(__file__).parent / "seen_ids.json"

translator = GoogleTranslator(source="it", target="en")
bot = Bot(token=BOT_TOKEN)


def load_seen_ids():
    if SEEN_IDS_FILE.exists():
        try:
            return set(json.loads(SEEN_IDS_FILE.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Could not load seen_ids: {e}. Starting fresh.")
    return set()


def save_seen_ids(seen_ids):
    try:
        SEEN_IDS_FILE.write_text(json.dumps(list(seen_ids)))
    except OSError as e:
        print(f"⚠️  Could not save seen_ids: {e}")


async def send_with_retry(text, max_retries=3):
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=GROUP_ID, text=text)
            return True
        except RetryAfter as e:
            print(f"⏳ Rate limit — waiting {e.retry_after}s...")
            await asyncio.sleep(e.retry_after)
        except (NetworkError, TimedOut) as e:
            wait = 2 ** attempt
            print(f"⚠️  Network error ({type(e).__name__}), retrying in {wait}s...")
            await asyncio.sleep(wait)
    print("❌ Failed to send message after max retries.")
    return False


async def main():
    seen_ids = load_seen_ids()

    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        messages = []
        async for msg in client.iter_messages(CHANNEL, limit=20):
            if msg.text:
                messages.append({"id": msg.id, "text": msg.text})
        messages.reverse()  # oldest first so we send in chronological order

    print(f"📨 Fetched {len(messages)} messages from {CHANNEL}")

    if not messages:
        print("⚠️  No messages fetched.")
        return

    # First run (empty cache): send latest as startup test, mark all as seen
    if not seen_ids:
        print("⏳ First run — sending latest message as startup test...")
        last = messages[-1]
        try:
            translated = translator.translate(last["text"])
        except Exception as e:
            translated = f"(translation failed: {e})"
        await send_with_retry(
            f"✅ GTT bot started — startup test\n\n"
            f"🇮🇹 Original:\n{last['text']}\n\n"
            f"🇬🇧 English:\n{translated}"
        )
        for msg in messages:
            seen_ids.add(msg["id"])
        save_seen_ids(seen_ids)
        print(f"✅ Marked {len(seen_ids)} messages. Next run will send only new ones.")
        return

    sent_count = 0
    for msg in messages:
        if msg["id"] in seen_ids:
            continue

        try:
            translated = translator.translate(msg["text"])
        except Exception as e:
            print(f"⚠️  Translation failed ({type(e).__name__}: {e}) — skipping.")
            continue

        sent = await send_with_retry(
            f"🚌 GTT Update\n\n"
            f"🇮🇹 Original:\n{msg['text']}\n\n"
            f"🇬🇧 English:\n{translated}"
        )
        if sent:
            seen_ids.add(msg["id"])
            save_seen_ids(seen_ids)
            sent_count += 1
            print(f"✅ Sent message {msg['id']}")

    if sent_count == 0:
        print("ℹ️  No new messages.")
    else:
        print(f"✅ Done — sent {sent_count} new message(s).")


if __name__ == "__main__":
    asyncio.run(main())
