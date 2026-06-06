import { loadMongoEnv } from './env.mjs';
import { MongoClient } from 'mongodb';

async function run() {
  const { uri, dbName, collectionName } = loadMongoEnv();
  const userId = process.argv[2];
  if (!userId) { console.log('❗ Usage: node scripts/delete-user.mjs <user_id>'); process.exit(1); }

  const client = new MongoClient(uri);
  await client.connect();
  const db = client.db(dbName);
  const coll = db.collection(collectionName);

  const user = await coll.findOne({ telegram_user_id: userId });
  if (!user) { console.log(`User ${userId} tidak ditemukan.`); await client.close(); return; }

  console.log(`Menghapus: ${user.name} (${userId})`);
  const r = await coll.deleteOne({ telegram_user_id: userId });
  console.log(`✅ Dihapus: ${r.deletedCount} user(s)`);
  await client.close();
}

run().catch(err => { console.error(err.message); process.exit(1); });
