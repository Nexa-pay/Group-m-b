import os
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait
from dotenv import load_dotenv

# Load variables from environment
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Make sure to add your personal Telegram User ID to your .env or Railway variables
OWNER_ID = int(os.getenv("OWNER_ID")) 

# Initialize Bot
app = Client(
    "my_telegram_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text("Hello! The bot is online and successfully deployed.")

# The mass ban command, restricted to the OWNER_ID
@app.on_message(filters.command("clean") & filters.user(OWNER_ID))
async def clean_group(client, message):
    # Check if the group ID was provided
    if len(message.command) < 2:
        await message.reply_text("⚠️ **Usage:** `/clean <target_group_id>`\nExample: `/clean -1001234567890`")
        return

    try:
        target_chat_id = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ Invalid Group ID format. It should be a number.")
        return

    status_msg = await message.reply_text(f"⏳ **Starting mass ban in** `{target_chat_id}`...\n*This might take a while depending on group size.*")
    
    banned_count = 0
    failed_count = 0

    try:
        # Fetch members from the target group
        async for member in client.get_chat_members(target_chat_id):
            # Skip bots, administrators, and the group creator
            if member.user.is_bot or member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                continue
                
            try:
                # Ban the user
                await client.ban_chat_member(target_chat_id, member.user.id)
                banned_count += 1
                
                # CRITICAL: Sleep to avoid hitting Telegram API limits
                await asyncio.sleep(0.5) 
                
            except FloodWait as e:
                # If Telegram says "slow down", pause the script for the requested time
                print(f"Sleeping for {e.value} seconds due to rate limits...")
                await asyncio.sleep(e.value)
            except Exception as e:
                failed_count += 1
                print(f"Failed to ban user {member.user.id}: {e}")

        # Update the final message once the loop is complete
        await status_msg.edit_text(
            f"✅ **Clean Complete!**\n\n"
            f"🚫 **Successfully Banned:** {banned_count}\n"
            f"⚠️ **Failed/Skipped:** {failed_count}"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error accessing group:**\n`{e}`\n\n*Make sure the bot is an admin in the target group with ban privileges.*")

if __name__ == "__main__":
    print("Bot is starting up...")
    app.run()
