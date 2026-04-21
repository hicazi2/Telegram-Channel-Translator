import asyncio
import os
from telethon import TelegramClient, events
from telegram import Bot
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

# Load secrets from .env file
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

# The GTT channel we want to listen to
GTT_CHANNEL = "@gttavvisi"

# Set up our tools
translator = GoogleTranslator(source="it", target="en")
bot = Bot(token=BOT_TOKEN)
client = TelegramClient("session", API_ID, API_HASH)

@client.on(events.NewMessage(pattern="/test"))
async def test_command(event):
    if event.is_private:  # only works in private message to yourself
        fake_italian = "Linea 4 limitata in piazza Vittorio. Causa lavori in corso Cairoli."
        translated_text = translator.translate(fake_italian)
        message = (
            f"🚌 *GTT Update*\n\n"
            f"🇮🇹 *Original:*\n{fake_italian}\n\n"
            f"🇬🇧 *English:*\n{translated_text}"
        )
        await bot.send_message(
            chat_id=GROUP_ID,
            text=message,
            parse_mode="Markdown"
        )
        print("✅ Test message sent!")
@client.on(events.NewMessage(chats=GTT_CHANNEL))
async def handle_new_message(event):
    original_text = event.message.text

    # Skip empty messages (like photos with no caption)
    if not original_text:
        return

    try:
        # Translate from Italian to English
        translated_text = translator.translate(original_text)

        # Format the message nicely
        message = (
            f"🚌 *GTT Update*\n\n"
            f"🇮🇹 *Original:*\n{original_text}\n\n"
            f"🇬🇧 *English:*\n{translated_text}"
        )

        # Send to your group
        await bot.send_message(
            chat_id=GROUP_ID,
            text=message,
            parse_mode="Markdown"
        )
        print(f"✅ Translated and forwarded: {translated_text[:50]}...")

    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🤖 Bot is running and listening to @gttavvisi...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())