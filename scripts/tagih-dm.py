#!/usr/bin/env python3
import os, sys, asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

WITA = timezone(timedelta(hours=8))

def log(msg):
    ts = datetime.now(WITA).strftime('%Y-%m-%d %H:%M WITA')
    print(f'[{ts}] {msg}')

def get_local_today():
    return datetime.now(WITA).strftime('%Y-%m-%d')

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

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session_str = os.environ.get("TELEGRAM_STRING_SESSION")
    mongo_uri = os.environ.get("MONGODB_URI")
    db_name = os.environ.get("MONGODB_DBNAME")
    coll_name = os.environ.get("MONGODB_COLLECTION")
    bot_token = os.environ.get("BOT_TOKEN")
    owner_id = os.environ.get("OWNER_ID")

    missing = [k for k, v in [
        ("TELEGRAM_API_ID", api_id),
        ("TELEGRAM_API_HASH", api_hash),
        ("TELEGRAM_STRING_SESSION", session_str),
        ("MONGODB_URI", mongo_uri),
    ] if not v]

    if missing:
        log(f"⚠️ Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    try:
        from pyrogram import Client, enums, errors
    except ImportError:
        os.system("pip install --no-cache-dir kurigram pymongo tgcrypto python-dotenv -q")
        from pyrogram import Client, enums, errors

    try:
        from pymongo import MongoClient as PyMongoClient
    except ImportError:
        os.system("pip install --no-cache-dir pymongo -q")
        from pymongo import MongoClient as PyMongoClient

    today = get_local_today()
    log(f"🔍 Cek member expired per {today}")

    mongo = PyMongoClient(mongo_uri)
    coll = mongo[db_name][coll_name]

    # Ambil user expired active — bedain yg bot_tgfs sama mirror
    mirror_users = list(coll.find({
        "expire_date": {"$lte": today},
        "status": "active",
        "plan": {"$ne": "bot_tgfs"},
    }))

    bot_tgfs_users = list(coll.find({
        "expire_date": {"$lte": today},
        "status": "active",
        "plan": "bot_tgfs",
    }))

    total_expired = len(mirror_users) + len(bot_tgfs_users)

    if not total_expired:
        msg = "✅ Gak ada user expired yg perlu ditagih lewat DM."
        log(msg)
        await send_owner_notif(bot_token, owner_id, msg)
        mongo.close()
        return

    log(f"📋 Ditemukan {len(mirror_users)} mirror + {len(bot_tgfs_users)} bot_tgfs expired")

    # Group bot_tgfs per customer biar 1 DM, bukan per bot
    bot_by_customer = {}
    for u in bot_tgfs_users:
        uid = u["telegram_user_id"]
        if uid not in bot_by_customer:
            bot_by_customer[uid] = []
        bot_by_customer[uid].append(u)

    # Build queue: (uid, name, mirror_doc or None, bot_list or [])
    user_queue = []
    for u in mirror_users:
        user_queue.append((u["telegram_user_id"], u.get("name", "User"), u, []))
    for uid, bots in bot_by_customer.items():
        first = bots[0]
        user_queue.append((uid, first.get("name", "User"), None, bots))

    try:
        async with Client(
            name="tagih_session",
            api_id=int(api_id),
            api_hash=api_hash,
            session_string=session_str,
            in_memory=True,
        ) as app:
            sent = 0
            skipped = 0
            failed = 0
            fail_details = []

            for uid, name, mirror_doc, bot_list in user_queue:
                check_doc = mirror_doc if mirror_doc else bot_list[0]
                last_dm = check_doc.get("billing", {}).get("last_user_dm_date", "")
                if last_dm == today:
                    log(f"⏭️  {uid} — {name}: udah di-DM hari ini, skip")
                    skipped += 1
                    continue

                # Build message
                if mirror_doc:
                    expire = mirror_doc.get("expire_date", "?")
                    msg = (
                        f"Hello sodara {name}, "
                        f"sekedar mengingatkan klok plan Drivecok Mirror sudah berakhir ({expire}), "
                        f"mau perpanjang atau izin udahan dulu? "
                        f"QRIS masih sama ya. "
                        f"Terima kasih! "
                        f"Semoga hari mu menyenangkan."
                    )
                else:
                    bot_lines = []
                    for b in bot_list:
                        bexp = b.get("expire_date", "?")
                        bbot = b.get("bot_username", b.get("bot_id", "?"))
                        bot_lines.append(f"  \u2022 {bbot} (expired {bexp})")
                    bot_str = "\n".join(bot_lines)
                    msg = (
                        f"Hello sodara {name}, sekedar mengingatkan bot kamu yang expired:\n"
                        f"{bot_str}\n\n"
                        f"Mau perpanjang? QRIS masih sama ya. "
                        f"Terima kasih! Semoga hari mu menyenangkan."
                    )

                try:
                    await app.send_message(
                        chat_id=int(uid),
                        text=msg,
                        parse_mode=enums.ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                    )
                    log(f"✅ DM terkirim ke {uid} — {name}")

                    # Update last_user_dm_date untuk semua doc terkait
                    if mirror_doc:
                        coll.update_one(
                            {"_id": mirror_doc["_id"]},
                            {"$set": {"billing.last_user_dm_date": today}},
                        )
                    else:
                        for b in bot_list:
                            coll.update_one(
                                {"_id": b["_id"]},
                                {"$set": {"billing.last_user_dm_date": today}},
                            )
                    sent += 1

                except errors.FloodWait as e:
                    log(f"⏳ FloodWait {e.value}s, tunggu dulu...")
                    await asyncio.sleep(e.value)
                    failed += 1
                    fail_details.append(f"{uid} — {name}: FloodWait {e.value}s")

                except errors.PeerIdInvalid:
                    log(f"⚠️ {uid} — {name}: PeerIdInvalid (akun dihapus/diblokir), skip")
                    failed += 1
                    fail_details.append(f"{uid} — {name}: PeerIdInvalid (akun invalid)")

                except errors.RPCError as e:
                    log(f"⚠️ RPCError DM {uid} — {name}: {e}")
                    failed += 1
                    fail_details.append(f"{uid} — {name}: {e}")

                except Exception as e:
                    log(f"⚠️ Gagal DM {uid} — {name}: {e}")
                    failed += 1
                    fail_details.append(f"{uid} — {name}: {e}")

                await asyncio.sleep(3)

            recap = f"📊 Selesai tagih DM: {sent} terkirim, {skipped} skip, {failed} gagal"
            log(recap)

            if fail_details and bot_token and owner_id:
                detail_text = "\n".join(fail_details[:10])
                await send_owner_notif(
                    bot_token, owner_id,
                    f"⚠️ *Tagih DM — Gagal*\n{recap}\n\n{detail_text}"
                )

    except Exception as e:
        log(f"⚠️ Fatal error: {e}")
        if bot_token and owner_id:
            await send_owner_notif(bot_token, owner_id, f"⚠️ *Tagih DM — Fatal*\n`{e}`")
        raise
    finally:
        mongo.close()

if __name__ == "__main__":
    asyncio.run(main())
