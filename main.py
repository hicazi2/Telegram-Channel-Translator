import os
import asyncio
import feedparser
import hashlib
from telegram import Bot
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

RSS_URL = "https://www.gtt.to.it/cms/avvisi-e-informazioni-di-servizio?format=feed&type=rss"

translator = GoogleTranslator(source="it", target="en")
bot = Bot(token=BOT_TOKEN)

seen_ids = set()

def get_entry_id(entry):
    raw = (entry.get("title", "") + entry.get("summary", ""))
    return hashlib.md5(raw.encode()).hexdigest()

async def check_feed():
    print("🔍 Checking GTT RSS feed...")
    try:
        feed = feedparser.parse(RSS_URL)
        print(f"📰 Found {len(feed.entries)} entries in feed")

        for entry in feed.entries:
            entry_id = get_entry_id(entry)
            if entry_id in seen_ids:
                continue
            seen_ids.add(entry_id)
            italian_text = entry.get("summary", entry.get("title", ""))
            if not italian_text:
                continue
            try:
                translated_text = translator.translate(italian_text)
                message = (
                    f"🚌 *GTT Update*\n\n"
                    f"🇮🇹 *Original:*\n{italian_text}\n\n"
                    f"🇬🇧 *English:*\n{translated_text}"
                )
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=message,
                    parse_mode="Markdown"
                )
                print(f"✅ Sent: {translated_text[:60]}...")
            except Exception as e:
                print(f"❌ Error sending message: {e}")
    except Exception as e:
        print(f"❌ Error fetching feed: {e}")

async def main():
    print("🤖 GTT Translator bot started!")
    print("📡 Polling RSS feed every 5 minutes...")
    print("⏳ Loading existing feed entries silently...")
    try:
        feed = feedparser.parse(RSS_URL)
        for entry in feed.entries:
            seen_ids.add(get_entry_id(entry))
        print(f"✅ Loaded {len(seen_ids)} existing entries. Watching for new ones...")
    except Exception as e:
        print(f"❌ Error on startup: {e}")

    while True:
        await check_feed()
        await asyncio.sleep(300)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise