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

    # === 3 kategori ===
    mirror_users = list(coll.find({
        "expire_date": {"$lte": today},
        "status": "active",
        "plan": {"$nin": ["bot_tgfs", "yt_premium"]},
    }))

    bot_tgfs_users = list(coll.find({
        "expire_date": {"$lte": today},
        "status": "active",
        "plan": "bot_tgfs",
    }))

    yt_premium_users = list(coll.find({
        "expire_date": {"$lte": today},
        "status": "active",
        "plan": "yt_premium",
    }))

    total_expired = len(mirror_users) + len(bot_tgfs_users) + len(yt_premium_users)

    if not total_expired:
        msg = "✅ Gak ada user expired yg perlu ditagih lewat DM."
        log(msg)
        await send_owner_notif(bot_token, owner_id, msg)
        mongo.close()
        return

    log(f"📋 Ditemukan {len(mirror_users)} mirror + {len(bot_tgfs_users)} bot_tgfs + {len(yt_premium_users)} yt_premium expired")

    # Group multi-doc plans per customer
    def group_by_user(docs):
        groups = {}
        for d in docs:
            uid = d["telegram_user_id"]
            if uid not in groups:
                groups[uid] = []
            groups[uid].append(d)
        return groups

    bot_groups = group_by_user(bot_tgfs_users)
    yt_groups = group_by_user(yt_premium_users)

    # Build queue: (uid, name, mirror_doc/None, bot_list/[], yt_list/[])
    user_queue = []
    for u in mirror_users:
        user_queue.append((u["telegram_user_id"], u.get("name", "User"), u, [], []))
    for uid, bots in bot_groups.items():
        first = bots[0]
        user_queue.append((uid, first.get("name", "User"), None, bots, []))
    for uid, yts in yt_groups.items():
        first = yts[0]
        user_queue.append((uid, first.get("name", "User"), None, [], yts))

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

            for uid, name, mirror_doc, bot_list, yt_list in user_queue:
                check_doc = mirror_doc or (bot_list[0] if bot_list else yt_list[0])
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
                elif bot_list:
                    lines = []
                    for b in bot_list:
                        bexp = b.get("expire_date", "?")
                        bbot = b.get("bot_username", b.get("bot_id", "?"))
                        lines.append(f"  \u2022 {bbot} (expired {bexp})")
                    msg = (
                        f"Hello sodara {name}, sekedar mengingatkan bot kamu yang expired:\n"
                        + "\n".join(lines) +
                        "\n\nMau perpanjang? QRIS masih sama ya. "
                        "Terima kasih! Semoga hari mu menyenangkan."
                    )
                elif yt_list:
                    lines = []
                    for y in yt_list:
                        bexp = y.get("expire_date", "?")
                        bgmail = y.get("gmail", "?")
                        username = y.get("username", "?")
                        uid_str = y.get("telegram_user_id", "?")
                        lines.append(f"  \u2022 {bgmail} (expired {bexp})")
                    msg = (
                        f"Hello {name} - {username} ({uid_str}), "
                        f"sekedar mengingatkan klok langganan YT Premium udah abis:\n"
                        + "\n".join(lines) +
                        "\n\nAyo gas renewal, QRIS yg sama ya, atau mau izin off ?"
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
                    docs_to_update = []
                    if mirror_doc:
                        docs_to_update.append(mirror_doc)
                    else:
                        docs_to_update.extend(bot_list)
                        docs_to_update.extend(yt_list)
                    for d in docs_to_update:
                        coll.update_one(
                            {"_id": d["_id"]},
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
