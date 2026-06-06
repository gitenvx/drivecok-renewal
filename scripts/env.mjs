import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

export function loadMongoEnv() {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const envPath = resolve(__dirname, '../.env');

  if (!existsSync(envPath)) {
    throw new Error(`Missing ${envPath}. Copy .env.example to .env first!`);
  }

  const raw = readFileSync(envPath, 'utf8');

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const match = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match) continue;

    const [, key, rawValue] = match;
    if (process.env[key] !== undefined) continue;

    process.env[key] = stripQuotes(rawValue.trim());
  }

  const required = ['MONGODB_URI', 'MONGODB_DBNAME'];
  const missing = required.filter((key) => !process.env[key]);

  if (missing.length) {
    throw new Error(`Missing required env: ${missing.join(', ')}`);
  }

  return {
    uri: process.env.MONGODB_URI,
    dbName: process.env.MONGODB_DBNAME,
    collectionName: process.env.MONGODB_COLLECTION || 'customers',
    BOT_TOKEN: process.env.BOT_TOKEN || null,
    groupChatId: process.env.GROUP_CHAT_ID || null,
    TELEGRAM_API_ID: process.env.TELEGRAM_API_ID ? Number(process.env.TELEGRAM_API_ID) : null,
    TELEGRAM_API_HASH: process.env.TELEGRAM_API_HASH || null,
    TELEGRAM_STRING_SESSION: process.env.TELEGRAM_STRING_SESSION || null,
    TELEGRAM_MFA: process.env.TELEGRAM_MFA || null,
    TELEGRAM_NUMBER: process.env.TELEGRAM_NUMBER || null,
    TELEGRAM_GRAMJS_SESSION: process.env.TELEGRAM_GRAMJS_SESSION || null
  };
}

function stripQuotes(value) {
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }

  return value;
}
