# CLAUDE.md — Drivecok Renewal

## Commands

### Customer Ops (run from project root)
- `node scripts/list-summary.mjs` — list all customers
- `node scripts/list-summary.mjs <user_id>` — check specific customer
- `node scripts/add-user.mjs <user_id> <username> <name> <plan> [expire_date]` — add customer
- `node scripts/renew-user.mjs <user_id> [date]` — renew (+1mo from DB expire_date default)
- `node scripts/kick-stop.mjs <user_id>` — kick + stop customer
- `node scripts/delete-user.mjs <user_id>` — permanently delete customer
- `node scripts/run-reminders.mjs` — send expiry reminders (cron)
- `venv/bin/python3 scripts/sync-check.py` — sync DB vs Telegram group members
- `venv/bin/python3 scripts/session.py` — generate Telegram string session

## Critical Rules

1. **Renew = from `expire_date` in DB**, not from today. Always.
2. **Default renew = +1 month.** Execute immediately, don't ask.
3. **Plan names:** `Group` or `Group_PrivateChatBot`. "PrivateChatBot" in user message → use `Group_PrivateChatBot`.
4. **Kick** auto-sends `/u <user_id>` if plan contains `PrivateChatBot`.
5. **Python** via `venv/bin/python3` (Linux/WSL).
6. **Timezone:** Asia/Makassar (GMT+8), not UTC.

## Context

See `CONTEXT.md` for full project overview. `MEMORY.md` for AI agent SOP.
