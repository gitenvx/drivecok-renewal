# 🧠 AI Agent Context — Drivecok Renewal

> **Customer Management System** for Telegram premium Group/Bot subscription services.
> Maintained by **Ucok** (dev & operator). Timezone: **Asia/Makassar (GMT+8)**.

## Tech Stack

| Layer | Tech |
|-------|------|
| Runtime | Node.js (ESM — `"type": "module"`) + Python 3 |
| Database | MongoDB (Atlas), collection: `customers` |
| OS | Linux / WSL |
| Python Deps | Pyrofork, PyMongo, TgCrypto |
| Repo | `github.com/gitenvx/drivecok-renewal` |

## Folder Layout

```
drivecok-renewal/
  .env              ← MongoDB URI, Bot Token, Telegram API creds
  scripts/          ← All operational scripts (Node.js .mjs + Python .py)
    add-user.mjs           Add new customer
    delete-user.mjs        Permanently remove customer
    kick-stop.mjs          Kick from group + stop + announcement
    list-summary.mjs       List active/expired/stopped customers
    renew-user.mjs         Extend subscription
    run-reminders.mjs      Auto-remind expiring users (cron) — kirim log + recap ke DM Owner & Grup
    import-customers.mjs   Bulk import from JSON
    env.mjs                .env config loader
    sync-check.py          Compare Telegram members vs DB
    session.py             Generate Pyrogram string session
    promo.py               Kirim promo ke GROUP_PROMOSI via user session (cron)
    promo.md               Isi pesan promosi — diedit langsung tanpa sentuh Python
  users/            ← JSON import samples
  venv/             ← Python virtual env (Pyrofork)
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
5. **Python** via `venv/bin/python3` (Linux/WSL path).
6. **Reminders:** Only send if `expire_date` is today or past, and `reminder_count_today < 3`. Max 3x/day.
   - Log & recap langsung dikirim ke DM Owner + Grup via Bot (gak ada file log lokal).
   - Jalan pake `npm run reminders` (via `--dns-result-order=ipv4first` untuk WSL).
7. **Promo content**: Edit `scripts/promo.md` — script Python tinggal baca dari file.
8. **Error handling:** If Telegram API returns 400/403/404, report code + description. Don't ignore.
8. **Default expire_date** when adding user without date = 1 month from today (or specific join date if Ucok mentions).

## Command Reference

### Customer Operations (from project root)
| Command | Description |
|---------|-------------|
| `node scripts/list-summary.mjs` | List all customers |
| `node scripts/list-summary.mjs <user_id>` | Check specific customer |
| `node scripts/add-user.mjs <user_id> <username> <name> <plan> [expire_date]` | Add customer |
| `node scripts/renew-user.mjs <user_id> [date]` | Renew (+1mo from DB expire_date default) |
| `node scripts/kick-stop.mjs <user_id>` | Kick + stop customer |
| `node scripts/delete-user.mjs <user_id>` | Permanently delete customer |

### Automation & Tools
| Command | Description |
|---------|-------------|
| `npm run reminders` (or `node --dns-result-order=ipv4first scripts/run-reminders.mjs`) | Send expiry reminders — kirim log + recap ke DM Owner & Grup (cron) |
| `venv/bin/python3 scripts/sync-check.py` | Sync DB vs Telegram group members |
| `venv/bin/python3 scripts/session.py` | Generate Telegram string session |
| `venv/bin/python3 scripts/promo.py` | Send promo to GROUP_PROMOSI (content from promo.md) |

## Related Docs

- `README.md` — full user guide
- `USER.md` — operator profile (Ucok)
- `IDENTITY.md` — AI assistant identity

## SOP for AI Agents

1. **Act autonomously.** If Ucok gives clear instruction ("renew user 12345"), execute directly. Don't reply "OK I will".
2. **Stay in project root.** All commands run from `drivecok-renewal/`.
3. **Only ask confirmation** if parameters are truly ambiguous (e.g. plan unclear when adding user).
4. **OS awareness:** Always use `venv/bin/python3`, not Windows paths.
5. **🚨 NO auto-push to GitHub.** Stage & commit only. Ucok must review and push himself.
6. **🚨 Always ask before creating new files.** Don't create new scripts or files without Ucok's approval.
