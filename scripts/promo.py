#!/usr/bin/env python3
import os
import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


WITA = timezone(timedelta(hours=8))

PROMO_FILE = Path(__file__).resolve().parent / 'promo.md'
PROMO_MSG = PROMO_FILE.read_text(encoding='utf-8').strip()

def log(msg):
    ts = datetime.now(WITA).strftime('%Y-%m-%d %H:%M WITA')
    print(f'[{ts}] {msg}')

async def send_owner_notif(bot_token, chat_id, text):
    try:
        import aiohttp
    except ImportError:
        os.system("pip install --no-cache-dir aiohttp -q")
        import aiohttp

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": int(chat_id),
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=payload, timeout=15) as resp:
                if not resp.ok:
                    err = await resp.text()
                    log(f"⚠️ Bot notif HTTP status {resp.status}: {err}")
                return resp.ok
    except asyncio.TimeoutError:
        log("⚠️ Bot notif timeout")
    except aiohttp.ClientError as e:
        log(f"⚠️ Bot notif network error (aiohttp): {e}")
    except Exception as e:
        log(f"⚠️ Bot notif failed: {e}")
    return False

async def main():
    try:
        from dotenv import load_dotenv
    except ImportError:
        os.system("pip install --no-cache-dir python-dotenv -q")
        from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')

    group_promosi_raw = os.environ.get("GROUP_PROMOSI")
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session_str = os.environ.get("TELEGRAM_STRING_SESSION")
    owner_id = os.environ.get("OWNER_ID")
    bot_token = os.environ.get("BOT_TOKEN")

    if not all([group_promosi_raw, api_id, api_hash, session_str, owner_id, bot_token]):
        log("⚠️ Missing env vars — GROUP_PROMOSI, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_STRING_SESSION, OWNER_ID, BOT_TOKEN")
        sys.exit(1)

    group_ids = [int(cid) for cid in group_promosi_raw.strip().split() if cid]
    if not group_ids:
        log("⚠️ GROUP_PROMOSI is empty")
        sys.exit(1)

    try:
        from pyrogram import Client, enums, errors
    except ImportError:
        os.system("pip install --no-cache-dir kurigram pymongo tgcrypto aiohttp python-dotenv -q")
        from pyrogram import Client, enums, errors

    now = datetime.now(WITA).strftime("%Y-%m-%d %H:%M WITA")
    msg = f"{PROMO_MSG}\n\n⏰ __{now}__\nBy OpenClawCok Ai Gateway"

    try:
        async with Client(
            name="promo_session",
            api_id=int(api_id),
            api_hash=api_hash,
            session_string=session_str,
            in_memory=True,
        ) as app:
            success = 0
            fail = 0
            for i, cid in enumerate(group_ids):
                if i > 0:
                    await asyncio.sleep(5)
                try:
                    await app.send_message(
                        chat_id=cid,
                        text=msg,
                        parse_mode=enums.ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                    )
                    log(f"✅ Promo terkirim ke {cid}")
                    success += 1
                except Exception as e:
                    log(f"⚠️ Gagal kirim ke {cid}: {e}")
                    fail += 1
                    await send_owner_notif(bot_token, owner_id, f"⚠️ Gagal kirim promo ke `{cid}`:\n`{e}`")

            recap = f"📊 Selesai: {success} berhasil, {fail} gagal dari {len(group_ids)} grup — {now}"
            log(recap)
            await send_owner_notif(bot_token, owner_id, recap)

    except Exception as e:
        err_msg = f"⚠️ Fatal error promo:\n`{e}`"
        log(err_msg)
        await send_owner_notif(bot_token, owner_id, err_msg)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
