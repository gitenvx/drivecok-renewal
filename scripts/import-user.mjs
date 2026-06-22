import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { MongoClient } from 'mongodb';
import { loadMongoEnv } from './env.mjs';

const args = process.argv.slice(2);
const shouldWrite = args.includes('--write');
const inputPathArg = args.find((arg) => arg !== '--write');

if (!inputPathArg) {
  console.error('Usage: node scripts/import-customers.mjs [--write] /users/customers.json');
  process.exit(1);
}

const config = shouldWrite ? loadMongoEnv() : { uri: null, dbName: null, collectionName: null };
const inputPath = resolve(process.cwd(), inputPathArg);
const rawJson = readFileSync(inputPath, 'utf8');
const input = JSON.parse(rawJson);

// Normalisasi: mapping langsung dari array user
const docs = input.map((u) => {
  const expireRaw = u.expire_date || u['Expired'] || '';
  let expire_date;
  if (/^\d{4}-\d{2}-\d{2}$/.test(expireRaw)) {
    expire_date = expireRaw;
  } else if (expireRaw) {
    // Coba parse format "1 June 2026"
    const d = new Date(expireRaw);
    if (!isNaN(d.getTime())) {
      expire_date = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Makassar', year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
    }
  }
  if (!expire_date) expire_date = new Date().toISOString().split('T')[0];

  return {
    telegram_user_id: String(u.telegram_user_id || u['UserID'] || u.id || ''),
    username: u.username || u['Username'] || '',
    name: u.name || u['Name'] || '(no name)',
    plan: u.plan || u['Plan'] || 'Group',
    email: u.email || '',
    expire_date,
    status: 'active',
    timezone: 'Asia/Makassar',
    billing: {
      reminder_enabled: true,
      reminder_count_today: 0,
      reminder_total: 0,
      last_reminded_at: null
    }
  };
});

const duplicates = findDuplicates(docs.map((doc) => doc.telegram_user_id));
if (duplicates.length) {
  throw new Error(`Duplicate telegram_user_id in input: ${duplicates.join(', ')}`);
}

console.log(`Input: ${inputPath}`);
console.log(`Normalized customers: ${docs.length}`);

if (docs.length) {
  console.log('First normalized customer preview:');
  console.log(JSON.stringify(docs[0], null, 2));
}

if (!shouldWrite) {
  console.log('Preview only. Add --write to upsert into MongoDB.');
  process.exit(0);
}

const client = new MongoClient(config.uri, {
  appName: 'telegram-renewal-import',
  serverSelectionTimeoutMS: 10000
});

try {
  await client.connect();
  const collection = client.db(config.dbName).collection(config.collectionName);

  const operations = docs.map((doc) => ({
    updateOne: {
      filter: { telegram_user_id: doc.telegram_user_id },
      update: {
        $set: doc,
        $setOnInsert: { created_at: new Date().toISOString() }
      },
      upsert: true
    }
  }));

  const result = await collection.bulkWrite(operations, { ordered: false });

  console.log('Import write complete');
  console.log(`Matched: ${result.matchedCount}`);
  console.log(`Modified: ${result.modifiedCount}`);
  console.log(`Upserted: ${result.upsertedCount}`);
} finally {
  await client.close();
}

function findDuplicates(values) {
  const seen = new Set();
  const duplicates = new Set();
  for (const value of values) {
    if (seen.has(value)) duplicates.add(value);
    seen.add(value);
  }
  return [...duplicates];
}
