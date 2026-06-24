#!/usr/bin/env python3

import asyncio
import json
import os
import sys, re
from datetime import datetime, timezone
from pathlib import Path
import aiohttp
from pyrogram import Client


def _load_env():
    ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
    if not os.path.exists(ENV_PATH):
        print(f"❌ File {ENV_PATH} tidak ditemukan")
        sys.exit(1)

    with open(ENV_PATH, 'r') as f:
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


_load_env()

BOT_TOKEN = os.environ['BOT_TOKEN']
OWNER_ID = int(os.environ['OWNER_ID'])
API_ID = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']

# ── Paths ─────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'logs'
STATE_FILE = DATA_DIR / 'emas-state.json'
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Sources ───────────────────────────────────────────────────
SOURCES = [
    {'name': 'Treasury', 'endpoint': 'treasury'},
    {'name': 'Antam', 'endpoint': 'anekalogam'},
]
BASE_URL = 'https://logam-mulia-api.iamutaki.workers.dev/api/prices'

# ── Helpers ───────────────────────────────────────────────────


def fmt(n: float | int) -> str:
    return 'Rp ' + f'{round(n):,}'.replace(',', '.')


def dir_emoji(diff: float) -> str:
    if diff > 0:
        return '🟢'
    if diff < 0:
        return '🔴'
    return '⚪'


def diff_str(diff: float) -> str:
    if diff == 0:
        return ''
    sign = '+' if diff > 0 else '-'
    return f' {sign}{fmt(abs(diff))}'


async def fetch_price(session: aiohttp.ClientSession, endpoint: str) -> dict:
    async with session.get(f'{BASE_URL}/{endpoint}') as resp:
        resp.raise_for_status()
        data = await resp.json()
        prices = data.get('data')
        if not prices:
            raise ValueError(f'{endpoint}: no data')
        # prefer 1-gram entry
        return next((d for d in prices if d.get('weight') == 1), prices[0])


# ── Main ──────────────────────────────────────────────────────


async def main():
    # ── load previous state ──
    state: dict = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except Exception:
            pass

    lines: list[str] = []
    now = datetime.now(timezone.utc)
    date_str = now.astimezone().strftime('%d %b %Y').upper()
    time_str = now.astimezone().strftime('%H:%M')

    # ── fetch prices ──
    async with aiohttp.ClientSession() as session:
        for src in SOURCES:
            try:
                price = await fetch_price(session, src['endpoint'])
            except Exception as e:
                lines.append(f'⚠️ {src["name"]}: skip ({e})')
                lines.append('')
                print(f'WARN: {src["name"]} skip — {e}')
                continue

            entry = {
                'sellPrice': price['sellPrice'],
                'buybackPrice': price['buybackPrice'],
                'recordedDate': price['recordedDate'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

            last = state.get(src['endpoint'])
            diff = entry['sellPrice'] - last['sellPrice'] if last else 0
            emoji = dir_emoji(diff)
            has_buyback = entry['buybackPrice'] > 0

            w = price.get('weight', '')
            wu = price.get('weightUnit', '')
            lines.append(f'{emoji} {src["name"]} {w}{wu}')
            lines.append(f'  Beli : {fmt(entry["sellPrice"])}{diff_str(diff)}')
            if has_buyback:
                diff_b = entry['buybackPrice'] - last['buybackPrice'] if last else 0
                lines.append(f'  Jual : {fmt(entry["buybackPrice"])}{diff_str(diff_b)}')
            lines.append('')

            state[src['endpoint']] = entry

    # ── persist state ──
    state['lastCheck'] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    # ── build message ──
    divider = '─' * 28
    output = (
        f'💰 HARGA EMAS\n'
        f'{date_str} {time_str} WITA\n'
        f'{divider}\n'
        f'{"\n".join(lines)}'
        f'{divider}'
    )

    # ── print to console ──
    print(output)

    # ── send to Telegram via kurigram ──
    app = Client('emas-bot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    async with app:
        try:
            await app.send_message(OWNER_ID, output)
        except Exception as e:
            print(f"Error sending message: {e}")


if __name__ == '__main__':
    asyncio.run(main())
