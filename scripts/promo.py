#!/usr/bin/env python3
"""
Kirim pesan promosi ke GROUP_PROMOSI via session Telegram user.
Jadwal: cron tiap 30 menit.
"""

import os
import re
import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# GMT+8
WITA = timezone(timedelta(hours=8))

LOG_FILE = Path(__file__).resolve().parent.parent / 'logs' / 'promo.log'

PROMO_FILE = Path(__file__).resolve().parent / 'promo.md'
PROMO_MSG = PROMO_FILE.read_text(encoding='utf-8').strip()

def log(msg):
    ts = datetime.now(WITA).strftime('%Y-%m-%d %H:%M WITA')
    line = f'[{ts}] {msg}'
    print(msg)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

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

async def main():
    load_env()

    # Clear log at start of each run
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text('')

    group_promosi_raw = os.environ.get("GROUP_PROMOSI")
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session_str = os.environ.get("TELEGRAM_STRING_SESSION")

    if not all([group_promosi_raw, api_id, api_hash, session_str]):
        log("ERROR: Missing env vars — GROUP_PROMOSI, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_STRING_SESSION")
        sys.exit(1)

    # Parse multiple chat IDs (space-separated)
    group_ids = [int(cid) for cid in group_promosi_raw.strip().split() if cid]
    if not group_ids:
        log("ERROR: GROUP_PROMOSI is empty")
        sys.exit(1)

    try:
        from pyrogram import Client, enums, errors
    except ImportError:
        log("Installing pyrogram...")
        os.system("pip install --no-cache-dir pyrofork pymongo tgcrypto -q")
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
                    log(f"❌ Gagal kirim ke {cid}: {e}")
                    fail += 1

            log(f"📊 Selesai: {success} berhasil, {fail} gagal dari {len(group_ids)} grup — {now}")
    except Exception as e:
        log(f"❌ Fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
