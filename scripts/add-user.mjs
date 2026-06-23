import { loadMongoEnv } from './env.mjs';
import { MongoClient } from 'mongodb';

async function run() {
  const { uri, dbName, collectionName } = loadMongoEnv();
  const args = process.argv.slice(2);
  
  if (args.length < 4) {
    console.log('❗ Usage: node scripts/add-user.mjs <user_id> <username> <name> <plan> [expire_date]');
    console.log('   Contoh: node scripts/add-user.mjs 6001872670 @lastthingV4 Hokage Group 2026-05-31');
    process.exit(1);
  }

  const [telegram_user_id, username, name, plan] = args;
  const expire_date = args[4] || new Date().toISOString().split('T')[0];
  const nowISO = new Date().toISOString();

  const client = new MongoClient(uri);
  await client.connect();
  const db = client.db(dbName);
  const coll = db.collection(collectionName);

  const existing = await coll.findOne({ telegram_user_id });
  if (existing) {
    console.log(`⚠️  User ${telegram_user_id} sudah ada di database.`);
    console.log(`   Nama: ${existing.name}, Expire: ${existing.expire_date}`);
    console.log('   Gunakan scripts/renew-user.mjs untuk renew.');
    await client.close();
    return;
  }

  await coll.insertOne({
    telegram_user_id,
    username: username || null,
    name: name || '(no name)',
    plan: plan || '—',
    expire_date,
    status: 'active',
    billing: {
      reminder_enabled: true,
      reminder_count_today: 0,
      reminder_total: 0,
      last_reminded_at: null,
      last_user_dm_date: null,
      created_at: nowISO
    }
  });

  console.log('━━━ USER BARU ━━━');
  console.log(`✅ UserID: ${telegram_user_id}`);
  console.log(`   Username: ${username || '—'}`);
  console.log(`   Name: ${name}`);
  console.log(`   Plan: ${plan}`);
  console.log(`   Expire: ${expire_date}`);
  console.log(`   Status: active`);
  
  await client.close();
}

run().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
