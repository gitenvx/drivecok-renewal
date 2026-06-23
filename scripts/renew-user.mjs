import { loadMongoEnv } from './env.mjs';
import { MongoClient } from 'mongodb';

async function run() {
  const { uri, dbName, collectionName } = loadMongoEnv();
  const args = process.argv.slice(2);
  let userId, customDate;

  if (args.length >= 1) {
    userId = args[0];
    customDate = args[1] || null;
  } else {
    userId = '6452023723'; // GANTI: fallback manual
    customDate = null;
  }

  if (!userId) {
    console.log('❗ Usage: node scripts/renew-user.mjs <user_id> [expire_date]');
    process.exit(1);
  }

  const client = new MongoClient(uri);
  try {
    await client.connect();
    const db = client.db(dbName);
    const coll = db.collection(collectionName);

    const user = await coll.findOne({ telegram_user_id: userId });
    if (!user) {
      console.log(`❌ User ${userId} tidak ditemukan.`);
      return;
    }

    let newExpire;
    if (customDate) {
      newExpire = customDate;
    } else {
      const d = new Date(user.expire_date);
      d.setMonth(d.getMonth() + 1);
      newExpire = new Intl.DateTimeFormat('en-CA', { 
        timeZone: 'Asia/Makassar', 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit' 
      }).format(d);
    }

    const old = user.expire_date;
    await coll.updateOne(
      { _id: user._id },
      {
        $set: {
          expire_date: newExpire,
          'billing.reminder_count_today': 0,
          'billing.last_reminded_at': null,
          'billing.last_user_dm_date': null,
          'billing.last_renewed_at': new Date().toISOString(),
          status: 'active'
        }
      }
    );

    console.log(`━━━ RENEW ━━━`);
    console.log(`✅ ${user.name || '(no name)'} (${userId})`);
    console.log(`   Plan: ${user.plan || '—'}`);
    console.log(`   Sebelum: ${old}`);
    console.log(`   Sesudah: ${newExpire}`);

  } finally {
    await client.close();
  }
}

run().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
