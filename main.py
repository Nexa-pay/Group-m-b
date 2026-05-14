import os
import asyncio
from pyrogram import Client, filters, enums, compose
from pyrogram.errors import FloodWait

# Load configurations from Environment Variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID")) # Your personal Telegram Account ID for security

# Client 1: The Userbot (Handles the heavy lifting to avoid Bot API limits)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Client 2: The Deepsikha Control Bot (Your DM interface)
deepsikha_bot = Client("deepsikha_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Listen ONLY in private DM and ONLY from you
@deepsikha_bot.on_message(filters.command("banall") & filters.private & filters.user(OWNER_ID))
async def ban_all_from_dm(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/banall <chat_id>`\nExample: `/banall -100123456789`")
        return

    target_chat = message.command[1]
    
    # Ensure the chat ID is parsed correctly
    try:
        target_chat = int(target_chat) if target_chat.lstrip('-').isdigit() else target_chat
    except ValueError:
        pass

    status_msg = await message.reply_text(f"⏳ **Deepsikha is scanning `{target_chat}`... This may take a moment.**")
    
    banned = 0
    failed = 0

    try:
        # The Userbot fetches and bans because standard bots have strict API limits
        async for member in userbot.get_chat_members(target_chat):
            # Skip group admins and the owner to prevent accidents
            if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                continue
            
            try:
                await userbot.ban_chat_member(target_chat, member.user.id)
                banned += 1
                
                # CRITICAL: Delay to protect the session string from getting banned
                await asyncio.sleep(0.5) 
                
                # Update your DM periodically so you know it's working
                if banned % 25 == 0:
                    await status_msg.edit_text(f"⏳ **Progress:** Banned `{banned}` members so far...")
                    
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await userbot.ban_chat_member(target_chat, member.user.id)
                banned += 1
            except Exception:
                failed += 1

        # Final Report sent to your Bot DM
        await status_msg.edit_text(
            f"✅ **Mass Ban Task Complete for `{target_chat}`**\n"
            f"Successfully banned: `{banned}` members\n"
            f"Failed/Skipped: `{failed}`\n"
            f"*(Admins were automatically skipped)*"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** Could not access chat. Make sure the Userbot is an admin in `{target_chat}`.\nError details: `{e}`")

async def main():
    print("Starting Deepsikha Control Bot and Userbot background processor...")
    # This runs both clients at the exact same time
    await compose([userbot, deepsikha_bot])

if __name__ == "__main__":
    asyncio.run(main())
