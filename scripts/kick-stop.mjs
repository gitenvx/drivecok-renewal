import { loadMongoEnv } from './env.mjs';

const env = loadMongoEnv();
const API = env.BOT_TOKEN ? `https://api.telegram.org/bot${env.BOT_TOKEN}` : null;
const GROUP_IDS = String(env.groupChatId || '').split(/\s+/).filter(Boolean);
const DB_URI = env.uri;
const DB_NAME = env.dbName;
const DB_COLL = env.collectionName;
const TARGET_USER_ID = process.argv[2];

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function tgCall(method, payload, retries = 3) {
  if (!API) return { ok: false, error: 'BOT_TOKEN tidak dikonfigurasi' };
  
  const url = `${API}/${method}`;
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      if (data.ok) return data;
      
      if (data.error_code === 400 || data.error_code === 403 || data.error_code === 404) {
        if (attempt < retries) {
          const w = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
          console.log(`    ⏳ Retry ${attempt}/${retries} — ${method}: ${data.description} (wait ${w}ms)...`);
          await delay(w);
        }
        continue;
      }
      
      if (attempt < retries) {
        const w = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        console.log(`    ⏳ Retry ${attempt}/${retries} — ${method}: ${data.description} (wait ${w}ms)...`);
        await delay(w);
      }
    } catch (err) {
      if (attempt < retries) {
        const w = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        console.log(`    ⏳ Retry ${attempt}/${retries} — ${method}: ${err.message} (wait ${w}ms)...`);
        await delay(w);
      } else {
        return { ok: false, error: `fetch failed after ${retries} retries: ${err.message}` };
      }
    }
  }
  return { ok: false, error: 'Max retries reached' };
}

async function getDbUser() {
  const { MongoClient } = await import('mongodb');
  const client = new MongoClient(DB_URI);
  try {
    await client.connect();
    return await client.db(DB_NAME).collection(DB_COLL).findOne({ telegram_user_id: TARGET_USER_ID });
  } finally {
    await client.close();
  }
}

async function stopUserInDb(user) {
  const { MongoClient } = await import('mongodb');
  const client = new MongoClient(DB_URI);
  try {
    await client.connect();
    await client.db(DB_NAME).collection(DB_COLL).updateOne(
      { _id: user._id },
      { 
        $set: { 
          status: 'stopped', 
          'billing.reminder_enabled': false, 
          'billing.stopped_at': new Date().toISOString() 
        } 
      }
    );
    console.log(`\n📦 DB: User ${TARGET_USER_ID} (${user.name}) → status stopped, reminder disabled ✅`);
  } finally {
    await client.close();
  }
}

async function run() {
  if (!TARGET_USER_ID) {
    console.error('❌ Usage: node scripts/kick-stop.mjs <user_id>');
    process.exit(1);
  }
  if (!API) {
    console.error('❌ BOT_TOKEN tidak ditemukan di .env');
    return;
  }
  if (!GROUP_IDS.length) {
    console.error('❌ GROUP_CHAT_ID tidak ditemukan');
    return;
  }

  const me = await tgCall('getMe', {});
  if (!me.ok) {
    console.error(`❌ Token bot tidak valid: ${me.description || me.error}`);
    return;
  }
  
  console.log(`✅ Bot: @${me.result.username}`);
  console.log(`📋 Group target: ${GROUP_IDS.join(', ')}`);
  console.log(`🎯 User target: ${TARGET_USER_ID}\n`);

  const user = await getDbUser();
  if (!user) {
    console.error(`❌ User ${TARGET_USER_ID} tidak ditemukan.`);
    return;
  }

  const username = user.username?.replace('@', '') || '(no username)';
  const name = user.name || '(no name)';
  const plan = user.plan || '—';
  const mention = username !== '(no username)' ? `@${username}` : name;
  const hasPCB = plan.toLowerCase().includes('privatechatbot');
  
  console.log(`👤 ${name} (${TARGET_USER_ID}) · Plan: ${plan} · PCB: ${hasPCB ? 'Ya ✅' : 'Tidak ❌'}`);

  for (const gid of GROUP_IDS) {
    console.log(`\n━━━ Group: ${gid} ━━━`);
    const k = await tgCall('kickChatMember', { chat_id: String(gid), user_id: Number(TARGET_USER_ID) });
    console.log(`  ${k.ok ? '✅ Kick: Berhasil' : `❌ Kick: Gagal — error_code=${k.error_code}, description="${k.description}"`}`);

    const msg = `@GDCOK telah menendang ${mention} - ${name} \`${TARGET_USER_ID}\` dari group karena gak lanjut langganan.\nPlan: ${plan}\nMengsedih!\n\n- Bot @openclawcokbot`;
    const m = await tgCall('sendMessage', { chat_id: String(gid), text: msg, parse_mode: 'Markdown', disable_web_page_preview: true });
    console.log(`  ${m.ok ? '✅ Pesan: Berhasil dikirim' : `❌ Pesan: Gagal — error_code=${m.error_code}, description="${m.description}"`}`);

    if (hasPCB) {
      const c = await tgCall('sendMessage', { chat_id: String(gid), text: `/u ${TARGET_USER_ID}`, disable_web_page_preview: true });
      console.log(`  ${c.ok ? '✅ CMD /u: Berhasil dikirim' : `❌ CMD /u: Gagal — error_code=${c.error_code}, description="${c.description}"`}`);
    }
  }

  await stopUserInDb(user);
  console.log(`\n━━━ SELESAI ━━━`);
}

run().catch(err => {
  console.error('FATAL:', err.message);
  process.exit(1);
});
