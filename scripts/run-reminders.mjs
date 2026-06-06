import { loadMongoEnv } from './env.mjs';

const env = loadMongoEnv();
const BOT_TOKEN = env.BOT_TOKEN;
const GROUP_CHAT_IDS = String(env.groupChatId || '').split(/\s+/).filter(Boolean);
const MONGO_URI = env.uri;
const DB_NAME = env.dbName;
const COLLECTION = env.collectionName;
const TELEGRAM_API = BOT_TOKEN ? `https://api.telegram.org/bot${BOT_TOKEN}` : null;
const TIMEZONE = 'Asia/Makassar';
const MAX_REMINDERS_PER_DAY = 3;
const CONFIG_COLLECTION = 'cron_config';

function getLocalToday() {
  return new Intl.DateTimeFormat('en-CA', { 
    timeZone: TIMEZONE, 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit' 
  }).format(new Date());
}

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function sendTelegramMessage(chatId, text) {
  if (!TELEGRAM_API) return { ok: false, error: 'BOT_TOKEN tidak dikonfigurasi' };
  
  const url = `${TELEGRAM_API}/sendMessage`;
  const MAX_RETRIES = 3;
  const TIMEOUT_MS = 15000;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
      
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          chat_id: String(chatId), 
          text, 
          parse_mode: 'HTML', 
          disable_web_page_preview: true 
        }),
        signal: controller.signal
      });
      
      clearTimeout(timer);
      const data = await res.json();
      
      if (data.ok) return data;
      
      if (data.error_code === 400 || data.error_code === 403 || data.error_code === 404) {
        console.log(`  ⏳ [${attempt}/${MAX_RETRIES}] sendMessage — ${data.description}`);
        if (attempt < MAX_RETRIES) {
          const w = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
          console.log(`    Retry in ${w}ms...`);
          await delay(w);
          continue;
        }
        return data;
      }
      
      if (attempt < MAX_RETRIES) {
        const w = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        console.log(`  ⏳ [${attempt}/${MAX_RETRIES}] sendMessage — ${data.description || 'unknown'}, retry in ${w}ms...`);
        await delay(w);
      }
    } catch (err) {
      if (attempt < MAX_RETRIES) {
        const w = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        console.log(`  ⏳ [${attempt}/${MAX_RETRIES}] sendMessage — ${err.message}, retry in ${w}ms...`);
        await delay(w);
      } else {
        console.error(`  ❌ All ${MAX_RETRIES} attempts failed for chat ${chatId}: ${err.message}`);
        return { ok: false, error: err.message };
      }
    }
  }
  return { ok: false, error: 'Max retries reached' };
}

function buildReminderMessage(customers, today) {
  if (!customers.length) return '';
  
  const lines = ['━━━ USER EXPIRED REMINDER ━━━', `📅 ${today} (${TIMEZONE})\n`];
  
  let n = 0;
  for (const c of customers) {
    n++;
    const name = c.name || '(No Name)';
    const uid = c.telegram_user_id;
    const plan = c.plan || '—';
    
    // Tap-to-copy ID
    const idCode = uid ? `(<code>${uid}</code>)` : '';
    
    // Prioritaskan username sebagai label link, kalau kosong pakai nama
    let userLabel = c.username ? (c.username.startsWith('@') ? c.username : `@${c.username}`) : name;
    
    // Pakai tg://user?id biar kebal walau usernamenya diganti
    const mentionLink = uid ? `<a href="tg://user?id=${uid}">${userLabel}</a>` : userLabel;
    
    const ov = c.days_overdue;
    const ds = ov === 0 ? 'Habis Hari Ini' : (ov === 1 ? 'Lewat 1 hari' : `Lewat ${ov} hari`);
    
    lines.push(`${n}. ${mentionLink} ${idCode}`);
    lines.push(`   — <b>${ds}</b>`);
    lines.push(`   Plan: ${plan}\n`);
  }
  
  lines.push('━━━━━━━━━━━━━━━━━━━');
  lines.push(`Segera renewal ke @GDCOK ya!`);
  lines.push(`Total: ${customers.length} user(s) | Bot: @openclawcokbot by @Drivecok`);
  
  return lines.join('\n');
}

async function run() {
  if (!BOT_TOKEN || !MONGO_URI) {
    console.error('FATAL: BOT_TOKEN atau MONGODB_URI tidak dikonfigurasi.');
    return;
  }
  
  const today = getLocalToday();
  const { MongoClient } = await import('mongodb');
  const client = new MongoClient(MONGO_URI);
  
  try {
    await client.connect();
    const db = client.db(DB_NAME);
    const customers = db.collection(COLLECTION);
    const cfg = db.collection(CONFIG_COLLECTION);
    
    const lastReset = await cfg.findOne({ _id: 'reminder_counter_reset_date' });
    if (!lastReset || lastReset.date !== today) {
      const r = await customers.updateMany(
        { 'billing.reminder_count_today': { $gt: 0 } },
        { $set: { 'billing.reminder_count_today': 0, 'billing.last_reminded_at': null } }
      );
      await cfg.updateOne(
        { _id: 'reminder_counter_reset_date' },
        { $set: { date: today, last_reset_at: new Date().toISOString() } },
        { upsert: true }
      );
      console.log(`  Counter reset untuk ${r.modifiedCount} pelanggan (hari baru: ${today})`);
    } else {
      console.log(`  Counter sudah direset hari ini (${today}).`);
    }

    const pending = await customers.find({
      expire_date: { $lte: today },
      status: 'active',
      'billing.reminder_enabled': true,
      'billing.reminder_count_today': { $lt: MAX_REMINDERS_PER_DAY }
    }).toArray();
    
    if (!pending.length) {
      console.log(`[${today}] No pending reminders.`);
      return;
    }

    const nowISO = new Date().toISOString();
    const data = [];
    
    for (const doc of pending) {
      const nc = (doc.billing?.reminder_count_today ?? 0) + 1;
      const nt = (doc.billing?.reminder_total ?? 0) + 1;
      
      await customers.updateOne(
        { _id: doc._id },
        { 
          $set: { 
            'billing.reminder_count_today': nc, 
            'billing.reminder_total': nt, 
            'billing.last_reminded_at': nowISO 
          } 
        }
      );
      
      const ed = doc.expire_date;
      const dv = Math.floor((new Date(today + 'T00:00:00').getTime() - new Date(ed + 'T00:00:00').getTime()) / 86400000);
      data.push({ 
        telegram_user_id: doc.telegram_user_id, 
        username: doc.username, 
        name: doc.name, 
        plan: doc.plan, 
        expire_date: ed, 
        days_overdue: dv 
      });
    }
    
    if (!GROUP_CHAT_IDS.length) {
      console.log('No group chat IDs in env.');
      return;
    }
    
    const msg = buildReminderMessage(data, today);
    console.log(`[${today}] Pending: ${data.length} pelanggan, Groups: ${GROUP_CHAT_IDS.join(', ')}`);
    
    for (const gid of GROUP_CHAT_IDS) {
      const r = await sendTelegramMessage(gid, msg);
      console.log(`  ${gid}: ${r.ok ? 'OK' : 'FAIL'}${r.ok ? '' : ' - ' + JSON.stringify(r)}`);
    }
  } finally {
    await client.close();
  }
}

run().catch(err => {
  console.error('FATAL:', err.message);
  process.exit(1);
});
