try:
    from pyrogram import Client, enums, errors
except ImportError as e:
    print(f"Missing import pyrogram: {e}")
    import os

    print("Will installing automatically pyrogram")
    os.system("pip install --no-cache-dir pyrofork pymongo tgcrypto")

import os
import re
import asyncio
from pyrogram import Client, enums, errors

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
                if m:
                    key, value = m.group(1), m.group(2).strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    os.environ[key] = value

async def ses() -> None:
    load_env()
    print("Required pyrogram V2 or greater.")
    
    API_KEY = os.environ.get("TELEGRAM_API_ID")
    if not API_KEY:
        API_KEY = input("Enter API KEY: ")
    else:
        print(f"Menggunakan TELEGRAM_API_ID dari .env: {API_KEY}")
        
    if not str(API_KEY).isdigit():
        print("Input integer please su")
        return await ses()
        
    API_HASH = os.environ.get("TELEGRAM_API_HASH")
    if not API_HASH:
        API_HASH = input("Enter API HASH: ")
    else:
        print("Menggunakan TELEGRAM_API_HASH dari .env: ***")

    async with Client(
        name="USS", api_id=int(API_KEY), api_hash=API_HASH, in_memory=True
    ) as user:
        output = "Sent to your saved messages!"
        try:
            await user.send_message(
                "me",
                f"#SESSION\n\n`{await user.export_session_string()}`\n\nSuccessfully!",
                parse_mode=enums.ParseMode.MARKDOWN,
            )
            print(output)
        except errors.UserIsBot:
            print(await user.export_session_string())


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(ses())
# end of gen session
