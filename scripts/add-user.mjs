import { loadMongoEnv } from './env.mjs';
import { MongoClient } from 'mongodb';

async function run() {
  const { uri, dbName, collectionName } = loadMongoEnv();
  const args = process.argv.slice(2);
  
  if (args.length < 4) {
    console.log('❗ Usage: node scripts/add-user.mjs <user_id> <username> <name> <plan> [expire_date] [bot_id] [bot_username] [gmail]');
    console.log('   Contoh (Group): node scripts/add-user.mjs 6001872670 @lastthingV4 Hokage Group 2026-05-31');
    console.log('   Contoh (bot_tgfs): node scripts/add-user.mjs 12345 @user Nama bot_tgfs 2026-07-01 tgfs_01 @BotTGFS1');
    console.log('   Contoh (yt_premium): node scripts/add-user.mjs 12345 @user Nama yt_premium 2026-07-01 user@gmail.com');
    process.exit(1);
  }

  const [telegram_user_id, username, name, plan] = args;

  // Plan-specific shift
  let expire_date, bot_id, bot_username, gmail;

  if (plan === 'yt_premium') {
    // yt_premium: <user_id> <username> <name> yt_premium <expire_date> <gmail>
    expire_date = args[4] || new Date().toISOString().split('T')[0];
    gmail = args[5] || null;
    if (!gmail) {
      console.log('❗ Plan yt_premium membutuhkan <gmail>.');
      console.log('   Contoh: node scripts/add-user.mjs 12345 @user Nama yt_premium 2026-07-01 user@gmail.com');
      process.exit(1);
    }
  } else if (plan === 'bot_tgfs') {
    // bot_tgfs: <user_id> <username> <name> bot_tgfs <expire_date> <bot_id> <bot_username>
    expire_date = args[4] || new Date().toISOString().split('T')[0];
    bot_id = args[5] || null;
    bot_username = args[6] || null;
    if (!bot_id || !bot_username) {
      console.log('❗ Plan bot_tgfs membutuhkan <bot_id> dan <bot_username>.');
      console.log('   Contoh: node scripts/add-user.mjs 12345 @user Nama bot_tgfs 2026-07-01 tgfs_01 @BotTGFS1');
      process.exit(1);
    }
  } else {
    // plan lain: <user_id> <username> <name> <plan> [expire_date]
    expire_date = args[4] || new Date().toISOString().split('T')[0];
  }
  const nowISO = new Date().toISOString();

  const client = new MongoClient(uri);
  await client.connect();
  const db = client.db(dbName);
  const coll = db.collection(collectionName);

  if (plan === 'bot_tgfs') {
    // bot_tgfs: cek duplicate bot_id
    const dup = await coll.findOne({ plan: 'bot_tgfs', bot_id });
    if (dup) {
      console.log(`⚠️  Bot ID "${bot_id}" sudah terdaftar untuk ${dup.name} (${dup.telegram_user_id}).`);
      await client.close();
      return;
    }
  } else if (plan === 'yt_premium') {
    // yt_premium: cek duplicate gmail
    const dup = await coll.findOne({ plan: 'yt_premium', gmail });
    if (dup) {
      console.log(`⚠️  Gmail "${gmail}" sudah terdaftar untuk ${dup.name} (${dup.telegram_user_id}).`);
      await client.close();
      return;
    }
  } else {
    // plan lain: 1 user_id = 1 doc
    const existing = await coll.findOne({ telegram_user_id });
    if (existing) {
      console.log(`⚠️  User ${telegram_user_id} sudah ada di database.`);
      console.log(`   Nama: ${existing.name}, Expire: ${existing.expire_date}`);
      console.log('   Gunakan scripts/renew-user.mjs untuk renew.');
      await client.close();
      return;
    }
  }

  const doc = {
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
  };

  if (bot_id) doc.bot_id = bot_id;
  if (bot_username) doc.bot_username = bot_username;
  if (gmail) doc.gmail = gmail;

  await coll.insertOne(doc);

  console.log('━━━ USER BARU ━━━');
  console.log(`✅ UserID: ${telegram_user_id}`);
  console.log(`   Username: ${username || '—'}`);
  console.log(`   Name: ${name}`);
  console.log(`   Plan: ${plan}`);
  console.log(`   Expire: ${expire_date}`);
  if (bot_id) console.log(`   BotID: ${bot_id}`);
  if (bot_username) console.log(`   BotUser: ${bot_username}`);
  if (gmail) console.log(`   Gmail: ${gmail}`);
  console.log(`   Status: active`);
  
  await client.close();
}

run().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
