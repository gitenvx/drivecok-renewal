# 🧠 AI Agent Context — Drivecok Renewal

> **Customer Management System** for Telegram premium Group/Bot subscription services.
> Maintained by **Ucok** (dev & operator). Timezone: **Asia/Makassar (GMT+8)**.

## Tech Stack

| Layer | Tech |
|-------|------|
| Runtime | Node.js (ESM — `"type": "module"`) + Python 3 |
| Database | MongoDB (Atlas), collection: `customers` |
| OS | Linux / WSL |
| Python Deps | Kurigram, PyMongo, TgCrypto |
| Repo | `github.com/gitenvx/drivecok-renewal` |

## Folder Layout

```
drivecok-renewal/
  .env              ← MongoDB URI, Bot Token, Telegram API creds
  scripts/          ← All operational scripts (Node.js .mjs + Python .py)
    add-user.mjs           Add new customer
    delete-user.mjs        Permanently remove customer
    stop-user.mjs          Kick from group + stop + announcement
    list-user.mjs       List active/expired/stopped customers
    renew-user.mjs         Extend subscription
    reminders-user.mjs      Auto-remind expiring users (cron) — kirim log + recap ke DM Owner & Grup
    tagih-dm.py             DM nagih via user session ke member expired (via run-tagih-dm.sh)
    sync-user.py            Sync DB vs Telegram group members (via run-sync-user.sh)
    emas.py                 Cek harga emas Treasury/Antam (via run-emas.sh)
    gen_session.py          Generate Telegram string session — langsung `python3 gen_session.py`
    promo.py                Kirim promo ke GROUP_PROMOSI (via run-promo.sh)
    promo.md                Isi promosi — edit langsung
    run-emas.sh             Shell wrapper: emas.py
    run-promo.sh             Shell wrapper: promo.py
    run-sync-user.sh         Shell wrapper: sync-user.py
    run-tagih-dm.sh          Shell wrapper: tagih-dm.py
    requirements.txt        Python deps (aiohttp, kurigram, tgcrypto, python-dotenv)
  users/            ← JSON import samples
  venv/             ← Python virtual env
```

## DB Schema (Collection: `customers`)

```json
{
  "telegram_user_id": "123456789",
  "username": "@user",
  "name": "Nama Pelanggan",
  "plan": "Group_PrivateChatBot",
  "expire_date": "2026-06-01",
  "status": "active",
  "billing": {
    "reminder_enabled": true,
    "reminder_count_today": 0,
    "last_reminded_at": null,
    "last_renewed_at": null,
    "last_user_dm_date": null,
    "stopped_at": null,
    "created_at": "2026-06-05T..."
  }
}
```

- **Plan types:** `Group`, `PrivateChatBot`, `Group_PrivateChatBot`
- **Status:** `active` | `stopped`
- **expire_date:** Format `YYYY-MM-DD`, timezone Asia/Makassar

## Critical Rules (Golden Rules)

1. **Renew = from `expire_date` in DB, not from today.** Jika user bayar telat, tetap hitung dari tanggal expired di sistem.
2. **Default renew = +1 month.** Execute immediately without asking.
3. **Plan names:** Jika user disebut "PrivateChatBot" → pakai `Group_PrivateChatBot`. Default = `Group`.
4. **Kick flow:** Kick from group → send announcement → send `/u <user_id>` to bot if plan contains `PrivateChatBot` → set DB status to `stopped`.
5. **Python** → `bash scripts/run-<skrip>.sh`. JANGAN `venv/bin/python3` langsung (kecuali gen_session.py).
6. **Node.js** → `node scripts/<skrip>.mjs`.
7. **Reminders (Bot):** Hanya kirim jika `expire_date` hari ini/sudah lewat dan `reminder_count_today < 2`. Max 2x/hari.
   - Langsung `node scripts/reminders-user.mjs` (cron).
   - Cron tiap 1 jam (menit 2), log ke `logs/cron-reminders.log`.
8. **Tagih DM (User Session):** DM nagih via `TELEGRAM_STRING_SESSION` ke member expired.
   - 1x/hari via field `billing.last_user_dm_date` (terpisah dari counter bot — zero konflik).
   - Cron tiap 1 jam (menit 0) via `bash scripts/run-tagih-dm.sh`.
   - Log ke `logs/cron-reminders.log`.
9. **Cek Harga Emas:** `bash scripts/run-emas.sh`. Fetch API logam-mulia, kirim ke DM Owner. Cron tiap 1 jam. State di `logs/emas-state.json`.
9. **Promo content:** Edit `scripts/promo.md` — script Python tinggal baca dari file.
10. **Error handling:** If Telegram API returns 400/403/404, report code + description. Don't ignore.
11. **Default expire_date** when adding user without date = 1 month from today (or specific join date if Ucok mentions).

## Command Reference

### Customer Operations (from project root)
| Command | Description |
|---------|-------------|
| `node scripts/list-user.mjs` | List all customers |
| `node scripts/list-user.mjs <user_id>` | Check specific customer |
| `node scripts/add-user.mjs <user_id> <username> <name> <plan> [expire_date]` | Add customer |
| `node scripts/renew-user.mjs <user_id> [date]` | Renew (+1mo from DB expire_date default) |
| `node scripts/stop-user.mjs <user_id>` | Kick + stop customer |
| `node scripts/delete-user.mjs <user_id>` | Permanently delete customer |

### Automation & Tools
| Command | Description |
|---------|-------------|
| `node scripts/reminders-user.mjs` | Reminders + recap ke DM Owner & Grup (cron tiap 1 jam) |
| `bash scripts/run-tagih-dm.sh` | DM nagih ke member expired via user session (cron) |
| `bash scripts/run-sync-user.sh` | Sync DB vs Telegram group members |
| `python3 scripts/gen_session.py` | Generate Telegram string session |
| `bash scripts/run-promo.sh` | Send promo to GROUP_PROMOSI (content from promo.md) |
| `bash scripts/run-emas.sh` | Cek harga emas Treasury & Antam (cron tiap 1 jam) |

## Related Docs

- `README.md` — full user guide
- `USER.md` — operator profile (Ucok)
- `IDENTITY.md` — AI assistant identity

## SOP for AI Agents

1. **Act autonomously.** If Ucok gives clear instruction ("renew user 12345"), execute directly. Don't reply "OK I will".
2. **Stay in project root.** All commands run from `drivecok-renewal/`.
3. **Only ask confirmation** if parameters are truly ambiguous (e.g. plan unclear when adding user).
4. **OS awareness:** Linux/WSL. Python via `bash scripts/run-*.sh`, bukan Windows path.
5. **🚨 NO auto-push to GitHub.** Stage & commit only. Ucok reviews before push.
6. **🚨 Always ask before creating new files.** Don't create new scripts or files without approval.

## Safe Development & Git Workflow
- **No Destructive Commands Without Backup**: Jangan pernah menjalankan perintah git destruktif (seperti `git restore`, `git checkout`, `git reset --hard`) atau melakukan operasi yang menimpa file lokal yang memiliki perubahan belum di-commit/push tanpa:
  1. Meminta persetujuan eksplisit dari pengguna terlebih dahulu.
  2. Membuat salinan cadangan (backup) lokal dari berkas target terlebih dahulu (misal disalin sebagai berkas `.bak` di dalam ruang kerja) sebelum menjalankan perintah tersebut.
