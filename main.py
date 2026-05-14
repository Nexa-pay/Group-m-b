import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, RPCError
from motor.motor_asyncio import AsyncIOMotorClient

# Force integers for IDs
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
MONGO_URL = os.getenv("MONGO_URL")

deepsikha_bot = Client("deepsikha_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["TaggerMasterDB"]
active_userbots = []

async def load_sessions():
    cursor = db["users"].find({"session": {"$exists": True, "$ne": ""}})
    async for doc in cursor:
        try:
            ub = Client(f"ub_{doc['_id']}", api_id=API_ID, api_hash=API_HASH, 
                        session_string=doc["session"], in_memory=True)
            await ub.start()
            active_userbots.append(ub)
            print(f"✅ Loaded Userbot: {doc.get('user_id')}")
        except Exception as e:
            print(f"❌ Failed to load session {doc.get('user_id')}: {e}")

# This will trigger on /banall OR .banall
@deepsikha_bot.on_message(filters.command(["banall"], prefixes=["/", "."]))
async def ban_all_handler(client, message):
    # SECURITY CHECK: Reply to the user if they are NOT the owner
    if message.from_user.id != OWNER_ID:
        await message.reply_text("🚫 **Access Denied:** You are not the authorized owner.")
        return

    if len(message.command) < 2:
        await message.reply_text("ℹ️ **Usage:** `/banall -100123456789` (Make sure there is a space!)")
        return

    target_chat = message.command[1]
    
    if not active_userbots:
        await message.reply_text("❌ **Error:** No active session strings found in database.")
        return

    status = await message.reply_text(f"⏳ **Starting...** Scanning `{target_chat}`")

    banned = 0
    try:
        # Use the first available userbot to get members
        async for member in active_userbots[0].get_chat_members(target_chat):
            if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                continue
            
            # Rotate through userbots for the ban
            ub = active_userbots[banned % len(active_userbots)]
            try:
                await ub.ban_chat_member(target_chat, member.user.id)
                banned += 1
                if banned % 10 == 0:
                    await status.edit(f"🔨 Banned `{banned}` users...")
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                continue

        await status.edit(f"✅ **Mass Ban Complete!**\nTotal Banned: `{banned}`")
    except Exception as e:
        await status.edit(f"❌ **Failed:** `{e}`")

async def main():
    await deepsikha_bot.start()
    await load_sessions()
    print("🤖 Deepsikha is live!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
