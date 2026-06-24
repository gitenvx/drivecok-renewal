#!/usr/bin/env python3
"""
sync-check.py — Bandingkan anggota grup Telegram dengan database MongoDB
Menggunakan Pyrogram (user session) untuk ambil semua anggota grup.
"""

import os
import re
import sys
from pymongo import MongoClient
from pyrogram import Client, enums
import asyncio
from pathlib import Path

def load_env():
    """Load .env.mongo file"""
    env_path = Path(__file__).resolve().parent.parent / '.env'
    
    if not os.path.exists(env_path):
        print(f"❌ File {env_path} tidak ditemukan")
        sys.exit(1)
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if m:
                key, value = m.group(1), m.group(2).strip()
                # Remove quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                os.environ[key] = value

async def main():
    load_env()
    
    # === Cek env ===
    required = ['MONGODB_URI', 'MONGODB_DBNAME']
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"❌ Missing required env: {', '.join(missing)}")
        return
    
    uri = os.environ['MONGODB_URI']
    db_name = os.environ['MONGODB_DBNAME']
    collection_name = os.environ.get('MONGODB_COLLECTION', 'customers')
    group_ids = os.environ.get('GROUP_CHAT_ID', '').split()
    
    api_id = os.environ.get('TELEGRAM_API_ID')
    api_hash = os.environ.get('TELEGRAM_API_HASH')
    session_string = os.environ.get('TELEGRAM_STRING_SESSION')
    
    if not api_id or not api_hash or not session_string:
        print("❌ TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_STRING_SESSION wajib ada")
        return
    
    if not group_ids:
        print("❌ GROUP_CHAT_ID tidak ditemukan")
        return
    
    # === Koneksi MongoDB ===
    mongo_client = MongoClient(uri)
    db = mongo_client[db_name]
    coll = db[collection_name]
    
    db_users = list(coll.find({}, {'telegram_user_id': 1, 'name': 1, 'status': 1, '_id': 0}))
    db_active_ids = set(u.get('telegram_user_id') for u in db_users if u.get('telegram_user_id') and u.get('status') == 'active')
    db_stopped_ids = set(u.get('telegram_user_id') for u in db_users if u.get('telegram_user_id') and u.get('status') == 'stopped')
    db_all_ids = set(u.get('telegram_user_id') for u in db_users if u.get('telegram_user_id'))
    
    print(f"📦 DB: {len(db_users)} user terdaftar\n")
    
    # === Koneksi Telegram (Pyrogram user session) ===
    app = Client(
        "sync_check_session",
        api_id=int(api_id),
        api_hash=api_hash,
        session_string=session_string,
        in_memory=True
    )
    
    async with app:
        me = await app.get_me()
        print(f"🔑 Login sebagai: {me.first_name or ''} {me.last_name or ''} (@{me.username or '-'})")
        print()
        
        for group_id in group_ids:
            print(f"━━━ Group: {group_id} ━━━")
            
            try:
                chat = await app.get_chat(int(group_id))
                total_members = chat.members_count if hasattr(chat, 'members_count') else '?'
                print(f"  Total anggota: {total_members}")
                
                # Ambil semua anggota grup
                group_member_ids = []
                async for member in app.get_chat_members(int(group_id)):
                    if member.user and not member.user.is_bot:
                        if member.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                            group_member_ids.append(str(member.user.id))
                
                print(f"  Anggota yg terambil (non-bot, non-admin): {len(group_member_ids)}")
                
                group_set = set(group_member_ids)
                
                not_in_db = [uid for uid in group_set if uid not in db_all_ids]
                stopped_but_in_group = [uid for uid in group_set if uid in db_stopped_ids]
                active_not_in_group = [uid for uid in db_active_ids if uid not in group_set]
                
                print(f"  Anggota grup terdaftar & aktif di DB: {len(group_set) - len(not_in_db) - len(stopped_but_in_group)}")
                print(f"  Anggota grup TIDAK di DB: {len(not_in_db)}")
                print(f"  Anggota grup status STOPPED: {len(stopped_but_in_group)}")
                print(f"  User DB AKTIF TIDAK ada di grup: {len(active_not_in_group)}")
                
                if not_in_db:
                    print(f"\n  ⚠️ Anggota grup tidak terdaftar di database:")
                    for uid in not_in_db:
                        try:
                            user = await app.get_users(int(uid))
                            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                            username = f"@{user.username}" if user.username else ''
                            print(f"     {uid} — {name} {username}")
                        except:
                            print(f"     {uid} — (gagal get info)")
                    print()
                    
                if stopped_but_in_group:
                    print(f"\n  🛑 User berstatus STOPPED tapi masih ada di grup:")
                    for uid in stopped_but_in_group:
                        db_info = next((u for u in db_users if u.get('telegram_user_id') == uid), None)
                        name = db_info.get('name', '(no name)') if db_info else '(no name)'
                        print(f"     {uid} — {name}")
                    print()
                
                if active_not_in_group:
                    print(f"\n  ⚠️ User database AKTIF tapi sudah tidak ada di grup:")
                    for uid in active_not_in_group:
                        db_info = next((u for u in db_users if u.get('telegram_user_id') == uid), None)
                        name = db_info.get('name', '(no name)') if db_info else '(no name)'
                        print(f"     {uid} — {name}")
                    print()
                
                if not not_in_db and not stopped_but_in_group and not active_not_in_group:
                    print("  ✅ Semua anggota grup sinkron dengan DB (aktif)")
                
            except Exception as e:
                print(f"  ❌ Gagal ambil anggota grup: {e}")
            
            print()
    
    mongo_client.close()

if __name__ == '__main__':
    asyncio.run(main())
