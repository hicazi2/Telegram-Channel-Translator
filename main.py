import os
import json
import asyncio
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from telegram import Bot
from telegram.error import RetryAfter, NetworkError, TimedOut
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

CHANNEL_URL = "https://t.me/s/gttavissi"
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


def fetch_messages():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GTTBot/1.0)"}
    try:
        resp = requests.get(CHANNEL_URL, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch channel page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    messages = []

    for wrap in soup.select(".tgme_widget_message_wrap"):
        msg_div = wrap.select_one(".tgme_widget_message[data-post]")
        if not msg_div:
            continue
        msg_id = msg_div.get("data-post", "").strip()
        text_div = wrap.select_one(".tgme_widget_message_text")
        if not msg_id or not text_div:
            continue
        text = text_div.get_text(separator="\n").strip()
        if text:
            messages.append({"id": msg_id, "text": text})

    return messages


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
    messages = fetch_messages()
    print(f"📨 Fetched {len(messages)} messages from channel")

    if not messages:
        print("⚠️  No messages fetched — channel may be unreachable.")
        return

    # First run (empty cache): send the latest message as a startup test, then mark all as seen
    if not seen_ids:
        print("⏳ First run — sending latest message as startup test...")
        last = messages[-1]
        try:
            translated = translator.translate(last["text"])
        except Exception as e:
            translated = f"(translation failed: {e})"
        test_text = (
            f"✅ GTT bot started — startup test\n\n"
            f"🇮🇹 Original:\n{last['text']}\n\n"
            f"🇬🇧 English:\n{translated}"
        )
        await send_with_retry(test_text)
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

        text = (
            f"🚌 GTT Update\n\n"
            f"🇮🇹 Original:\n{msg['text']}\n\n"
            f"🇬🇧 English:\n{translated}"
        )

        sent = await send_with_retry(text)
        if sent:
            seen_ids.add(msg["id"])
            save_seen_ids(seen_ids)
            sent_count += 1
            print(f"✅ Sent: {msg['id']}")

    if sent_count == 0:
        print("ℹ️  No new messages.")
    else:
        print(f"✅ Done — sent {sent_count} new message(s).")


if __name__ == "__main__":
    asyncio.run(main())
