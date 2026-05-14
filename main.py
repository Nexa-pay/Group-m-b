import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, AuthKeyUnregistered
from motor.motor_asyncio import AsyncIOMotorClient

# --- Configuration ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
MONGO_URL = os.getenv("MONGO_URL")

# --- Initialize Control Bot & Database ---
deepsikha_bot = Client("deepsikha_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["TaggerMasterDB"]
users_collection = db["users"]

# List to hold all our active Userbot clients
active_userbots = []

async def load_sessions_from_db():
    """Fetches all sessions from MongoDB and starts them."""
    print("Loading sessions from TaggerMasterDB...")
    
    # Find all documents where the "session" field exists and is not empty
    cursor = users_collection.find({"session": {"$exists": True, "$ne": ""}})
    
    async for doc in cursor:
        session_str = doc.get("session")
        user_id = doc.get("user_id")
        
        try:
            # Create a Pyrogram client for this specific session
            ub = Client(
                f"userbot_{user_id}", 
                api_id=API_ID, 
                api_hash=API_HASH, 
                session_string=session_str,
                in_memory=True # Don't create .session files on Railway
            )
            await ub.start()
            active_userbots.append(ub)
            
            me = await ub.get_me()
            print(f"✅ Successfully loaded session: {me.first_name} (ID: {me.id})")
            
        except AuthKeyUnregistered:
            print(f"❌ Session for {user_id} is dead/revoked. Consider deleting it from DB.")
        except Exception as e:
            print(f"⚠️ Could not load session for {user_id}: {e}")
            
    print(f"🎉 Total active userbots loaded: {len(active_userbots)}")


@deepsikha_bot.on_message(filters.command("banall") & filters.user(OWNER_ID) & filters.private)
async def ban_all_logic(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Provide a Chat ID: `/banall -100...`")

    if not active_userbots:
        return await message.reply_text("❌ No active userbots loaded from the database!")

    target_chat = message.command[1]
    
    try:
        target_chat = int(target_chat) if target_chat.lstrip('-').isdigit() else target_chat
    except ValueError:
        pass

    status = await message.reply_text(f"⏳ **Deepsikha is initiating mass ban using {len(active_userbots)} accounts...**")

    banned = 0
    bot_index = 0 # Used to rotate between accounts
    current_ub = active_userbots[bot_index]

    try:
        # We use the FIRST bot to fetch the member list
        async for member in current_ub.get_chat_members(target_chat):
            if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                continue
            
            # --- The Banning Logic with Auto-Rotation ---
            ban_successful = False
            while not ban_successful:
                try:
                    await current_ub.ban_chat_member(target_chat, member.user.id)
                    banned += 1
                    ban_successful = True
                    await asyncio.sleep(0.3) # Standard delay
                    
                except FloodWait as e:
                    # If this bot hits a limit, switch to the NEXT bot in the pool immediately!
                    print(f"Bot {bot_index} got FloodWait. Rotating...")
                    bot_index = (bot_index + 1) % len(active_userbots)
                    current_ub = active_userbots[bot_index]
                    await asyncio.sleep(0.1) 
                    
                except Exception as e:
                    # If there's a different error (like missing admin rights), skip the user
                    ban_successful = True 

            # Update DM progress
            if banned % 25 == 0:
                await status.edit(f"🔨 Banned `{banned}` users so far... (Rotating across {len(active_userbots)} accounts)")

        await status.edit(f"✅ **Mass Ban Complete!** Banned `{banned}` members in `{target_chat}`.")
        
    except Exception as e:
        await status.edit(f"❌ **Error:** Make sure at least one of the userbots is an Admin in the group.\nDetails: `{e}`")

async def main():
    print("Starting Deepsikha Services...")
    # 1. Start the main DM control bot
    await deepsikha_bot.start()
    
    # 2. Connect to MongoDB and load all sessions
    await load_sessions_from_db()
    
    print("✅ Deepsikha is online and waiting for commands in DM!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
