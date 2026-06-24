import { loadMongoEnv } from './env.mjs';
import { MongoClient } from 'mongodb';

function fmt(u) {
  let label = `${u.telegram_user_id || '?'} - ${u.name || '(no name)'} - ${u.expire_date || '—'}`;
  if (u.plan === 'bot_tgfs') label += ` | ${u.bot_username || u.bot_id || '?'}`;
  return label;
}

function getLocalToday() {
  return new Intl.DateTimeFormat('en-CA', { 
    timeZone: 'Asia/Makassar', 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit' 
  }).format(new Date());
}

async function run() {
  const { uri, dbName, collectionName } = loadMongoEnv();
  const args = process.argv.slice(2);
  const specificUser = args[0];
  const planFilter = args.find(a => a.startsWith('--plan='))?.split('=')[1] || null;

  const client = new MongoClient(uri);
  try {
    await client.connect();
    const db = client.db(dbName);
    const coll = db.collection(collectionName);

    // Mode: cek user spesifik
    if (specificUser) {
      const users = await coll.find({ telegram_user_id: specificUser }).toArray();
      if (!users.length) {
        console.log(`❌ User ${specificUser} tidak ditemukan.`);
        return;
      }

      for (const user of users) {
        console.log(`━━━ DETAIL USER ━━━`);
        console.log(`   ID: ${user.telegram_user_id}`);
        console.log(`   Nama: ${user.name || '(no name)'}`);
        console.log(`   Username: ${user.username || '—'}`);
        console.log(`   Plan: ${user.plan || '—'}`);
        console.log(`   Expire: ${user.expire_date || '—'}`);
        console.log(`   Status: ${user.status || '—'}`);
        if (user.plan === 'bot_tgfs') {
          console.log(`   BotID: ${user.bot_id || '—'}`);
          console.log(`   BotUsername: ${user.bot_username || '—'}`);
        }
        console.log('');
      }
      return;
    }

    // Mode: ringkasan
    const query = planFilter ? { plan: planFilter } : {};
    const users = await coll.find(query).toArray();
    if (!users.length) {
      console.log('📭 Tidak ada pelanggan.');
      return;
    }

    const today = getLocalToday();
    const stopped = [];
    const expired = [];
    const aktif = [];
    
    for (const u of users) {
      if (u.status === 'stopped') {
        stopped.push(u);
      } else if (u.expire_date && u.expire_date <= today) {
        expired.push(u);
      } else {
        aktif.push(u);
      }
    }

    const s = (a, b) => (a.expire_date || 'z').localeCompare(b.expire_date || 'z');
    stopped.sort(s);
    expired.sort(s);
    aktif.sort(s);

    console.log(`━━━ RINGKASAN PELANGGAN ━━━`);
    console.log(`📅 ${today} (Asia/Makassar)\nTotal: ${users.length} pelanggan\n`);
    
    if (stopped.length) {
      console.log(`🛑 Stopped: ${stopped.length}`);
    }
    if (expired.length) {
      console.log(`❌ Expired (${expired.length}):`);
      expired.forEach(u => console.log(`   ${fmt(u)}`));
      console.log('');
    }
    if (aktif.length) {
      console.log(`✅ Aktif (${aktif.length}):`);
      aktif.forEach(u => console.log(`   ${fmt(u)}`));
      console.log('');
    }

  } finally {
    await client.close();
  }
}

run().catch(e => {
  console.error('FATAL:', e.message);
  process.exit(1);
});
