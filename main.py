# --- Standard library imports (built into Python, no installation needed) ---
import os        # reads environment variables (your secrets like BOT_TOKEN)
import json      # saves/loads data in JSON format (a simple text-based storage format)
import asyncio   # lets Python do multiple things without waiting — needed because Telegram API calls take time
import html      # escapes special HTML characters (<, >, &) so Telegram's HTML parser doesn't break
from pathlib import Path  # a cleaner way to work with file paths on any operating system
from zoneinfo import ZoneInfo  # converts UTC timestamps to Italy's local time

# --- Telethon: reads messages FROM Telegram as a real user ---
# This is what lets the bot log in as YOU and read the gttavvisi channel.
# A regular bot cannot read channels it's not an admin of — but a user account can.
from telethon import TelegramClient
from telethon.sessions import StringSession  # StringSession stores your login in a single string (stored as a GitHub Secret)

# --- python-telegram-bot: sends messages TO your group ---
# This is a separate library from Telethon. It uses your bot (created via @BotFather)
# to send the translated messages into your group chat.
from telegram import Bot
from telegram.error import RetryAfter, NetworkError, TimedOut, BadRequest  # specific error types we handle gracefully

# --- requests: makes HTTP calls to the Azure Translator API ---
import requests

# --- python-dotenv: loads secrets from a .env file when running locally ---
# On GitHub Actions, secrets come from the repository settings instead.
from dotenv import load_dotenv


# Load the .env file if it exists (only relevant when running on your own computer)
load_dotenv()

# Read all secrets from environment variables.
# int() converts the string value to a number where needed.
API_ID = int(os.getenv("API_ID"))           # your Telegram API id (from my.telegram.org)
API_HASH = os.getenv("API_HASH")            # your Telegram API hash (from my.telegram.org)
SESSION_STRING = os.getenv("SESSION_STRING") # your saved Telethon login session
BOT_TOKEN = os.getenv("BOT_TOKEN")          # your bot's token (from @BotFather)
GROUP_ID = int(os.getenv("GROUP_ID"))       # the ID of the group to send messages to
AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")      # Azure Translator API key
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION")  # Azure resource region (e.g. "eastus")

CHANNEL = "gttavvisi"  # the Telegram channel username to read from

# Path to the file that stores which message IDs have already been sent.
# __file__ is this script's location. .parent is its folder. We store seen_ids.json next to it.
SEEN_IDS_FILE = Path(__file__).parent / "seen_ids.json"

def translate(text):
    """Translate Italian text to English using the Azure Translator API."""
    response = requests.post(
        "https://api.cognitive.microsofttranslator.com/translate",
        params={"api-version": "3.0", "from": "it", "to": "en"},
        headers={
            "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
            "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
            "Content-Type": "application/json",
        },
        json=[{"text": text}],
        timeout=10,
    )
    response.raise_for_status()
    return response.json()[0]["translations"][0]["text"]


def load_seen_ids():
    """Load the set of already-sent message IDs from disk.
    Returns an empty set if the file doesn't exist yet (e.g. first run)."""
    if SEEN_IDS_FILE.exists():
        try:
            # json.loads turns the saved text back into a Python list, then set() removes duplicates
            return set(json.loads(SEEN_IDS_FILE.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Could not load seen_ids: {e}. Starting fresh.")
    return set()


def save_seen_ids(seen_ids):
    """Save the current set of seen message IDs to disk so the next run remembers them."""
    try:
        # json.dumps turns the Python set into a JSON-formatted string we can write to a file
        SEEN_IDS_FILE.write_text(json.dumps(list(seen_ids)))
    except OSError as e:
        print(f"⚠️  Could not save seen_ids: {e}")


async def send_with_retry(bot, text, max_retries=3):
    """Send a message to the Telegram group. Retries up to 3 times if it fails.

    Telegram sometimes rate-limits bots (too many messages too fast) or has
    brief network issues. This function handles those cases automatically."""
    for attempt in range(max_retries):
        try:
            await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode="HTML")
            return True
        except RetryAfter as e:
            # Telegram told us to wait a specific number of seconds before retrying.
            # Cap at 30s so a long rate-limit doesn't block the entire job.
            wait = min(e.retry_after, 30)
            print(f"⏳ Rate limit — waiting {wait}s (Telegram requested {e.retry_after}s)...")
            await asyncio.sleep(wait)
        except BadRequest as e:
            # A permanent API error (e.g. invalid chat_id, message too long).
            # Retrying will never fix this, so fail immediately.
            print(f"❌ Bad request (will not retry): {e}")
            return False
        except (NetworkError, TimedOut) as e:
            # A general connection problem — wait longer each attempt (1s, 2s, 4s)
            wait = 2 ** attempt
            print(f"⚠️  Network error ({type(e).__name__}), retrying in {wait}s...")
            await asyncio.sleep(wait)
    print("❌ Failed to send message after max retries.")
    return False


async def main():
    # Load the list of message IDs we've already sent (from the GitHub Actions cache)
    seen_ids = load_seen_ids()

    # --- Connect to Telegram as a user (via Telethon) ---
    # StringSession(SESSION_STRING) restores your saved login — no phone number prompt needed
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()

    # Make sure the session is still valid. If not, the user needs to regenerate it.
    if not await client.is_user_authorized():
        print("❌ Session is not authorized. Please regenerate SESSION_STRING.")
        await client.disconnect()
        return

    # Fetch the last 20 messages from the gttavvisi channel.
    # We only keep messages that have text (some posts are photos or stickers with no text).
    messages = []
    async for msg in client.iter_messages(CHANNEL, limit=20):
        if msg.text:
            messages.append({"id": msg.id, "text": msg.text, "date": msg.date})

    # iter_messages returns newest first, so we reverse to process oldest first.
    # This ensures messages are sent to the group in chronological order.
    messages.reverse()
    await client.disconnect()

    print(f"📨 Fetched {len(messages)} messages from {CHANNEL}")

    if not messages:
        print("⚠️  No messages fetched.")
        return

    # Use Bot as an async context manager so the HTTP session is properly
    # initialized and torn down (required by python-telegram-bot v20+).
    async with Bot(token=BOT_TOKEN) as bot:
        # --- First run (seen_ids is empty, meaning no cache exists yet) ---
        # Instead of silently doing nothing, we send the most recent message as a
        # startup confirmation so you can verify the bot is working end-to-end.
        if not seen_ids:
            print("⏳ First run — sending latest message as startup test...")
            last = messages[-1]  # the most recent message (last after reversing)
            try:
                translated = translate(last["text"])
            except Exception as e:
                translated = f"(translation failed: {e})"
            await send_with_retry(
                bot,
                f"✅ GTT bot is now running.\n"
                f"This is the most recent message from @gttavvisi at the time of startup:\n\n"
                f"<b>{html.escape(translated)}</b>\n\n"
                f"─────🚌─────\n\n"
                f"🇮🇹 Original message from @gttavvisi:\n{html.escape(last['text'])}\n\n"
                f"⏰ {last['date'].astimezone(ZoneInfo('Europe/Rome')).strftime('%H:%M')} | 📅 {last['date'].astimezone(ZoneInfo('Europe/Rome')).strftime('%d %b %Y')}"
            )
            # Mark all current messages as seen so they aren't re-sent next run
            for msg in messages:
                seen_ids.add(msg["id"])
            save_seen_ids(seen_ids)
            print(f"✅ Marked {len(seen_ids)} messages. Next run will send only new ones.")
            return

        # --- Normal run: check for new messages and send them ---
        sent_count = 0
        for msg in messages:
            # Skip this message if we've already sent it in a previous run
            if msg["id"] in seen_ids:
                continue

            # Translate the Italian text to English.
            # On failure, fall back to "(translation unavailable)" so the message is
            # still delivered and marked as seen — without this, a persistently failing
            # translation would silently re-queue the message on every run forever.
            translation_failed = False
            try:
                translated = translate(msg["text"])
            except Exception as e:
                print(f"⚠️  Translation failed ({type(e).__name__}: {e}) — sending original.")
                translation_failed = True

            # Send the bilingual message to the group
            if translation_failed:
                sent = await send_with_retry(
                    bot,
                    f"🚌  GTT Update  🔔\n\n"
                    f"⚠️ Translation failed\n\n"
                    f"─────🚌─────\n\n"
                    f"🇮🇹 Original message from @gttavvisi:\n{html.escape(msg['text'])}\n\n"
                    f"⏰ {msg['date'].astimezone(ZoneInfo('Europe/Rome')).strftime('%H:%M')} | 📅 {msg['date'].astimezone(ZoneInfo('Europe/Rome')).strftime('%d %b %Y')}"
                )
            else:
                sent = await send_with_retry(
                    bot,
                    f"🚌  GTT Update  🔔\n\n"
                    f"<b>{html.escape(translated)}</b>\n\n"
                    f"─────🚌─────\n\n"
                    f"🇮🇹 Original message from @gttavvisi:\n{html.escape(msg['text'])}\n\n"
                    f"⏰ {msg['date'].astimezone(ZoneInfo('Europe/Rome')).strftime('%H:%M')} | 📅 {msg['date'].astimezone(ZoneInfo('Europe/Rome')).strftime('%d %b %Y')}"
                )
            if sent:
                # Mark this message as seen and save immediately.
                # We save after each message so progress isn't lost if something crashes mid-run.
                seen_ids.add(msg["id"])
                save_seen_ids(seen_ids)
                sent_count += 1
                print(f"✅ Sent message {msg['id']}")

        if sent_count == 0:
            print("ℹ️  No new messages.")
        else:
            print(f"✅ Done — sent {sent_count} new message(s).")


# This is the entry point — Python runs this block when you execute the script directly.
# asyncio.run() starts the async engine and runs our main() function inside it.
if __name__ == "__main__":
    asyncio.run(main())
