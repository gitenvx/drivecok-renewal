# 🚀 Drivecok Renewal

Halo! Selamat datang di repo **Drivecok Renewal**. Ini adalah *Customer Management System* (sistem manajemen pelanggan) yang dirancang khusus untuk mengurus operasional langganan layanan Group/Bot premium Telegram.

Semua data pelanggan tersimpan rapi di MongoDB, dan gue menggunakan kumpulan skrip Node.js & Python (dijalankan via `run-*.sh`) untuk mempermudah hidup—mulai dari nambahin user baru, perpanjang langganan, sampai nge-kick otomatis kalau masa aktifnya habis.

---

## 📁 Struktur Folder

Biar gampang navigasinya, ini ringkasan isi foldernya:

```text
drivecok-renewal/
├── .env                ← File setting utama (MongoDB, Bot Token, dll). Bikin dari .env.sample ya!
├── README.md           ← File yang lagi lo baca sekarang.
├── package.json        ← Daftar dependencies Node.js.
├── users/              ← Folder buat nyimpen data JSON (kalau butuh import awal).
├── venv/               ← Virtual environment Python.
└── scripts/            ← Inti dari repo ini! Semua skrip operasional ada di sini:
    ├── *.mjs               ← Skrip Node.js — `node scripts/xxx.mjs`
    ├── *.py                ← Skrip Python — dijalankan via shell wrapper:
    │   ├── run-*.sh        ← `bash scripts/run-<skrip>.sh`
    │   └── gen_session.py  ← Langsung `python3 scripts/gen_session.py`
    ├── add-user.mjs        ← Tambah pelanggan baru.
    ├── delete-user.mjs     ← Hapus data pelanggan.
    ├── emas.py             ← Cek harga emas (via run-emas.sh).
    ├── env.mjs             ← Utility narik .env.
    ├── import-user.mjs     ← Import data massal dari JSON.
    ├── list-user.mjs       ← Cek status pelanggan.
    ├── renew-user.mjs      ← Perpanjang masa aktif.
    ├── reminders-user.mjs  ← Bot reminder expired (via cron).
    ├── stop-user.mjs       ← Kick user, kirim pengumuman, update status.
    ├── tagih-dm.py         ← DM nagih via user session (via run-tagih-dm.sh).
    ├── sync-user.py        ← Sinkron member grup vs DB (via run-sync-user.sh).
    ├── promo.py            ← Kirim iklan (via run-promo.sh).
    ├── promo.md            ← Isi teks promosi.
    └── run-*.sh            ← Shell wrapper utk semua skrip Python
```

---

## 🛠️ Instalasi & Persiapan Awal

Biar skripnya jalan dengan mulus, ikuti langkah instalasi ini dulu ya:

### 1. Setup Node.js (Untuk Skrip Utama)
Pastikan lo udah install Node.js. Lalu install dependencies-nya:
```bash
# Masuk ke folder project
cd drivecok-renewal

# Install library yang dibutuhin (dotenv, mongodb, dll)
npm install
```

### 2. Setup Python (Untuk Fitur Sync & Session)
Skrip `sync-user.py` dan `gen_session.py` jalan pakai Python (Pyrogram). Biar rapi, gue bikin *virtual environment*:
```bash
# Bikin virtual environment
python3 -m venv venv

# Aktifkan virtual environment
# Di Linux/Mac:
source venv/bin/activate
# Di Windows:
venv\Scripts\activate

# Install dependencies Python
pip install kurigram pymongo tgcrypto
```

### 3. Generate String Session
Biar skrip sinkronisasi bisa narik data anggota dari grup Telegram, gue butuh "String Session" layaknya login biasa. Tinggal jalanin skrip bawaan ini:
```bash
# Pastikan virtual environment Python udah aktif
python scripts/gen_session.py
```
- Skrip bakal otomatis narik **API ID** dan **API HASH** dari file `.env` lo. (Kalau belum ada di `.env`, baru akan diminta masukin manual).
- Terus masukin nomor HP dan kode OTP dari Telegram.
- String session lo bakal muncul di layar atau dikirim ke *Saved Messages* di Telegram. Salin string itu!

---

## ⚙️ Konfigurasi (`.env`)

Setelah instalasi selesai, pastikan lo setup file `.env` dari `.env.sample`. Formatnya kayak gini:

```env
MONGODB_URI="url_mongodb_lo"
MONGODB_DBNAME="nama_database"
MONGODB_COLLECTION="nama_collection"
GROUP_CHAT_ID="-100xxxxxx"
OWNER_ID="1181409600"

BOT_TOKEN="token_dari_botfather"

TELEGRAM_API_ID=12345
TELEGRAM_API_HASH="hash_dari_mytelegram"
TELEGRAM_STRING_SESSION="...string_gen_session.pyrogram_lo..."
```

**Penjelasan singkat:**
- `GROUP_CHAT_ID`: ID grup Telegram tujuan (kalau lebih dari satu, pisahin pakai spasi). Semua kick, reminder, dan sync-check bakal beroperasi di grup-grup ini.
- `OWNER_ID`: ID Telegram lo — reminder & log akan dikirim ke DM ini via Bot.
- `BOT_TOKEN`: Token bot lo (dapat dari BotFather).
- `TELEGRAM_API_ID` & `TELEGRAM_API_HASH`: Ambil dari my.telegram.org. Ini wajib buat login *user session*.
- `TELEGRAM_STRING_SESSION`: Sesi login akun lo via Pyrogram biar skrip bisa baca daftar member grup layaknya akun beneran (dipakai buat `sync-user.py`).

---

## 👤 Sekilas Tentang Data Pelanggan

Data pelanggan gue simpan di collection `customers` MongoDB dengan format kayak gini:

```javascript
{
  telegram_user_id: "1181409600",   // ID unik user di Telegram
  username: "@GDCOK",                // Username Telegram (bisa kosong kalau user ga set)
  name: "Ucok",                      // Nama yang tampil
  plan: "Group_PrivateChatBot",      // Paket langganan: "Group" atau "PrivateChatBot" / "Group_PrivateChatBot"
  expire_date: "2026-08-01",         // Masa aktif (Format: YYYY-MM-DD, zona waktu Asia/Makassar)
  status: "active",                  // Statusnya: "active" atau "stopped"
  billing: {
    reminder_enabled: true,          // Mau dingetin gak pas mau expired?
    reminder_count_today: 0,         // Udah berapa kali dingetin hari ini (maksimal 2)
    last_reminded_at: null,          // Kapan terakhir dikirimi pesan reminder
    last_renewed_at: null,           // Kapan terakhir perpanjang
    last_user_dm_date: null,         // Terakhir di-DM tagih user session (YYYY-MM-DD)
    stopped_at: null,                // Kapan distop (kalau statusnya stopped)
    created_at: "2026-06-05T..."     // Kapan data ini pertama kali dibuat
  }
}
```

### 💡 Aturan Main Perpanjangan (Renew)
**Penting nih:** Kalau ada user yang perpanjang langganan, sistem bakal ngehitung nambahnya **dari tanggal expired yang ada di database**, bukan dari hari ini dia bayar. 
*Contoh:* Expired di sistem `2026-06-01`. User bayar telat di tanggal `2026-06-05`. Masa aktif barunya tetap jadi `2026-07-01` (+1 bulan dari data DB). Adil kan?

---

## 🚀 Panduan Menggunakan Skrip (Workflow)

Semua skrip gue operasikan dari terminal. **Pastikan lo udah ada di root folder project ini ya!**

### 0. Pilihan Paket (Plan)
Waktu nambahin atau ngubah user, ada 2 jenis paket utama:
- **`Group`**: Cuma dapet akses grup.
- **`PrivateChatBot`** (atau `Group_PrivateChatBot`): Akses grup + PrivateChatBot.
*(Catatan: Kalau paketnya ada kata `PrivateChatBot`, bot bakal otomatis ngejalanin command `/u <user_id>` sesudah nge-kick user tersebut).*

### 1. Lihat Daftar Pelanggan 📋
Pengen tau siapa aja yang aktif, expired, atau udah stop?
```bash
# Lihat ringkasan keseluruhan
node scripts/list-user.mjs

# Cek detail spesifik buat satu user
node scripts/list-user.mjs <user_id>
```

### 2. Tambah Pelanggan Baru ➕
Ada member baru? Langsung masukin ke sistem:
```bash
node scripts/add-user.mjs <user_id> <username> <name> <plan> [expire_date]

# Contoh penggunaan:
node scripts/add-user.mjs "1234" "@durov" "Durov" "Group" "2026-05-31"
```
*(Kalau `expire_date` gak diisi, default-nya bakal otomatis diset ke hari ini).*

### 3. Perpanjang Masa Aktif (Renew) 🔄
User habis transfer? Tinggal ketik ini:
```bash
# Tambah otomatis 1 bulan dari tanggal expired di DB
node scripts/renew-user.mjs <user_id>

# Atau, set manual ke tanggal tertentu
node scripts/renew-user.mjs <user_id> 2026-09-01
```

### 4. Stop & Kick User 🛑
Kalau user milih berhenti atau expired terlalu lama, skrip ini bakal ngerjain semuanya: 
1. Nge-kick dari grup, 
2. Ngirim pengumuman,
3. Cabut akses PrivateChatBot (via `/u <user_id>`),
4. Update status DB jadi `stopped`.

```bash
node scripts/stop-user.mjs <user_id>
```

### 5. Hapus User Sampai Bersih 🗑️
Kalau benar-benar mau ngapus data pelanggan dari database:
```bash
node scripts/delete-user.mjs <user_id>
```

### 6. Reminder Otomatis (Cron Job) ⏰
Tinggal jalanin ini (biasanya diset biar jalan otomatis lewat cron tiap 1 jam):
```bash
npm run reminders
# atau
node --dns-result-order=ipv4first scripts/reminders-user.mjs
```
- Kirim pengingat ke grup via Bot.
- Batas maksimal 2x sehari per user.
- Recap pelanggan expired dikirim dalam format rapi.

### 7. Tagih DM User Session 💬
DM nagih via akun user (`TELEGRAM_STRING_SESSION`) ke member yg expired:
```bash
bash scripts/run-tagih-dm.sh
```
- Counter field `billing.last_user_dm_date` — **1x/hari**, zero konflik dgn bot reminders.
- Error `PeerIdInvalid` (akun dihapus/diblokir) dilewatin otomatis.
- Cron tiap 1 jam di menit 0.

### 8. Cek Harga Emas 💰
Cek harga emas Treasury & Antam terkini:
```bash
bash scripts/run-emas.sh
```
- Fetch dari API logam-mulia, banding harga sebelumnya.
- Kirim hasil ke DM Owner via bot.
- State & log di `logs/`.
- Cron tiap 1 jam.

### 9. Promosi Broadcast 🎯
Kirim pesan promosi ke GROUP_PROMOSI otomatis:
```bash
bash scripts/run-promo.sh
```
**Edit pesan promosi** gampang — tinggal ubah `scripts/promo.md`, gak perlu sentuh Python.

### 10. Sinkronisasi Data (Sync-Check) 🔍
Pernah kepikiran, "Jangan-jangan ada orang di grup Telegram tapi datanya gak ada di DB?" Skrip ini ngecek silang anggota grup vs MongoDB.

```bash
bash scripts/run-sync-user.sh
```
Outputnya:
- Berapa orang yang datanya sinkron.
- Siapa aja pendatang gelap (ada di grup tapi gak ada di DB).
- Siapa aja yang udah "stopped" tapi masih nongkrong di grup.
- Skip owner, admin, dan bot.

---

## ⚠️ Penanganan Error (Error Handling)

Kalau Telegram API lagi rewel, jangan panik. Skrip gue udah dilengkapi sistem **retry otomatis (maksimal 3 kali)**.
Kalau bot benar-benar gagal (misal gagal nge-kick), pesan errornya bakal dicetak dengan detail:
`❌ Kick: Gagal — Telegram: error_code=404, description="Not Found"`

**Bocoran kode error umum:**
- `400`: Parameter salah (Bad Request).
- `403`: Bot diblokir atau gak punya akses admin di grup.
- `404`: User atau grup tidak ditemukan (misal user udah leave grup duluan).

---

## 🧠 Untuk Agent / AI

**Aturan penting saat menjalankan workflow:**

1. **Aturan Renew:** Selalu hitung penambahan masa aktif dari `expire_date` di database, **bukan** dari tanggal hari ini.
2. **Aturan Kick:** Eksekusi secara berurutan: Kick -> Kirim pengumuman -> Kirim `/u` (jika plan mengandung PrivateChatBot) -> Update status DB jadi `stopped`.
3. **Eksekusi Sync-Check:** Panggil via `bash scripts/run-sync-user.sh` dari folder `drivecok-renewal/`.
4. **Error Telegram:** Cetak `error_code` dan `description` dengan detail — jangan diabaikan.
5. **Semua perintah** wajib dijalankan dari direktori `drivecok-renewal/`:
   ```bash
   cd /home/mohfa/.openclaw/workspace/drivecok-renewal
   node scripts/<skrip>.mjs [args...]      # Node.js
   bash scripts/run-<skrip>.sh              # Python (via shell wrapper)
   python3 scripts/gen_session.py            # Khusus gen session aja
   ```
6. **Skrip Python** → pake `run-*.sh`, JANGAN panggil `venv/bin/python3` langsung (kecuali gen_session.py).
7. **Jika ragu:** Tanya ke Ucok dulu. Jangan asal eksekusi.

---

*Dibuat dengan sepenuh hati untuk mempermudah operasional Drivecok.*
