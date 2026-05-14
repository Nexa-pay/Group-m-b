import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, AuthKeyUnregistered, RPCError

# Environment Variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Initialize Clients
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
deepsikha_bot = Client("deepsikha_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@deepsikha_bot.on_message(filters.command("banall") & filters.user(OWNER_ID) & filters.private)
async def ban_all_logic(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Provide a Chat ID: `/banall -100...`")

    target_chat = message.command[1]
    status = await message.reply_text("⏳ **Connecting to Userbot...**")

    try:
        banned = 0
        # Use Pyrogram v2 async iterator
        async for member in userbot.get_chat_members(target_chat):
            if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                continue
            
            try:
                await userbot.ban_chat_member(target_chat, member.user.id)
                banned += 1
                await asyncio.sleep(0.5) # Anti-Flood
                
                if banned % 10 == 0:
                    await status.edit(f"🔨 Banned `{banned}` users...")
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                continue

        await status.edit(f"✅ **Done!** Banned `{banned}` members in `{target_chat}`.")
    except Exception as e:
        await status.edit(f"❌ **Error:** `{e}`")

async def start_services():
    print("Checking Session Health...")
    try:
        await userbot.start()
        await deepsikha_bot.start()
        
        # Verify Userbot is actually logged in
        me = await userbot.get_me()
        print(f"✅ Userbot started as: {me.first_name}")
        print(f"✅ Control Bot is online!")
        
        # Keep the script running
        await asyncio.Event().wait()
    except AuthKeyUnregistered:
        print("❌ ERROR: Your SESSION_STRING is expired or revoked! Generate a new one.")
    except Exception as e:
        print(f"❌ unexpected Error: {e}")
    finally:
        await userbot.stop()
        await deepsikha_bot.stop()

if __name__ == "__main__":
    asyncio.run(start_services())
