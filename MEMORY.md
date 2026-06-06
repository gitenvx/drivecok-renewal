# 🧠 AI Long-Term Memory: Drivecok Renewal

Dokumen ini adalah ingatan jangka panjang dan Standar Operasional Prosedur (SOP) untuk Agent AI. 
**PENTING: Selalu rujuk aturan di bawah ini sebelum mengeksekusi tugas terkait pelanggan.**

## 👤 Profil Pengguna
- **Nama:** Ucok (Mamas Ucok)
- **Pekerjaan:** 
  1. Penjual Nasi Goreng (nasgorcok.com) di Denpasar, Bali.
  2. Freelance Programmer (spesialis Bot Telegram & Next.js).

## ⚙️ Environment & Setup
- **Root Direktori Kerja:** `/home/mfa/.openclaw/workspace/drivecok-renewal` 
  *(Semua eksekusi perintah terminal HARUS dilakukan dari direktori ini)*
- **Sistem Operasi:** Linux / WSL via OpenClaw (Gunakan sintaks bash/shell Linux, misal `venv/bin/python3` untuk virtual environment).
- **Timezone:** Asia/Makassar (GMT+8)
- **Konfigurasi Utama:** File `.env` memuat MongoDB URI, Bot Token, Telegram API ID/Hash, dan Session String.

## 🗄️ Struktur Database (MongoDB)
- **Database:** (Dari `.env`) | **Collection:** `customers`
- **Data Shape Utama:**
  ```json
  {
    "telegram_user_id": "123456789",
    "name": "Nama Pelanggan",
    "plan": "Group_PrivateChatBot", // Jenis: Group, PrivateChatBot, Group_PrivateChatBot
    "expire_date": "2026-06-01",    // PENTING: Format YYYY-MM-DD
    "status": "active",             // active | stopped
    "billing": {
      "reminder_enabled": true,
      "reminder_count_today": 0     // Maksimal 3x kirim per hari
    }
  }
  ```

## 💡 SOP Eksekusi Skrip Operasional

Sebagian besar tugas dikerjakan melalui skrip Node.js dan Python yang sudah ada di folder `scripts/`.

### 1. Perpanjang Masa Aktif (Renew)
**Perintah:** `node scripts/renew-user.mjs <user_id> [tanggal_baru]`
- **CRITICAL RULE:** Saat User minta "renew", tambahkan masa aktif **DARI `expire_date` DI DATABASE**, bukan dari tanggal hari ini!
- **CRITICAL RULE:** Jika User tidak menyebutkan berapa bulan, **default +1 bulan** secara instan tanpa perlu bertanya.
- Skrip ini otomatis mereset `reminder_count_today` menjadi 0.

### 2. Berhentikan Pelanggan (Stop / Kick)
**Perintah:** `node scripts/kick-stop.mjs <user_id>`
- Jika User minta "kick" atau "stop", eksekusi skrip ini. 
- Skrip akan otomatis: Kick dari grup ➔ Kirim pengumuman ➔ Kirim perintah `/u <user_id>` (jika plan ada `PrivateChatBot`) ➔ Ubah status DB menjadi `stopped`.

### 3. Tambah Pelanggan Baru (Add)
**Perintah:** `node scripts/add-user.mjs <user_id> <username> <name> <plan> [expire_date]`
- Default `plan` adalah **`Group`**. Jika Ucok spesifik menyebut "privatechat" atau "privatechatbot", maka gunakan plan **`Group_PrivateChatBot`**.
- Default masa aktif jika dikosongkan adalah 1 bulan dari (*hari ini* kecuali ucok menyebut spesifik tanggal join nya.)

### 4. Pengecekan Anggota (Sync-Check)
**Perintah:** `venv/bin/python3 scripts/sync-check.py`
- Digunakan untuk membandingkan anggota riil di grup Telegram dengan data di MongoDB.
- Otomatis mengabaikan Admin, Owner, dan Bot.
- Akan menandai user "Pendatang Gelap" (di grup tapi tidak ada di DB), atau "User Stopped" yang belum di-kick.

### 5. Ringkasan Pelanggan (List Summary)
**Perintah:** `node scripts/list-summary.mjs [user_id]`
- Menampilkan daftar pelanggan aktif, expired, dan jumlah pelanggan stopped.

### 6. Hapus Pelanggan Secara Permanen (Delete)
**Perintah:** `node scripts/delete-user.mjs <user_id>`

### 7. Reminder Otomatis (Cron Job)
**Perintah:** `node scripts/run-reminders.mjs`
- Berjalan via cron job (`*/30 0-22 * * *`). 
- Hanya mengirim pesan jika `expire_date` sudah lewat atau pas di hari yang sama, dan `reminder_count_today` < 3.

## 🤖 Aturan Emas (Golden Rules) untuk AI Agent
1. **Bertindak Otonom:** Jika Ucok memberi instruksi jelas seperti "renew user 12345", **langsung eksekusi skripnya!** Jangan membuang waktu dengan menjawab "Oke, saya akan melakukannya."
2. **Konteks OS (Linux/WSL):** Ingat bahwa sistem adalah Linux/WSL. Saat mengeksekusi Python, pastikan memanggil `venv/bin/python3` (bukan `venv\Scripts\python.exe`).
3. **Penanganan Error Telegram:** Jika API Telegram merespons dengan Error (400/403/404), laporkan detail error-nya (Code & Description). Jangan diabaikan.
4. **Bertanya Jika Kritis:** Hanya tanyakan konfirmasi kepada Ucok jika parameter tidak lengkap/ambigu (contoh: minta renew tapi plan-nya belum jelas saat buat user baru).
