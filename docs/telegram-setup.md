# 🧰 Telegram Setup (Bot & Chat ID)

### 1) Buat bot
- Chat ke **@BotFather** → /newbot → ikuti instruksi → salin **BOT TOKEN**.

### 2) Masukkan bot ke grup (private boleh)
- Buka grup → Add member → cari bot → Add.
- (Channel?) Jadikan bot **Admin** agar bisa kirim pesan.

### 3) Dapatkan Chat ID grup (angka negatif -100…)
Cara A — `getUpdates`:
1. Kirim pesan apa saja di grup (mis. `ping`).
2. Buka di browser:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates?allowed_updates=["my_chat_member","message","channel_post"]`
3. Cari blok:
```json
"chat": { "id": -1001234567890, "title": "...", "type": "supergroup" }
```
Ambil `id` itu sebagai **chat_id** grup.

Tips jika kosong:
- Di @BotFather → **/setprivacy** → pilih bot → **Disable**.
- Hapus & tambahkan ulang bot ke grup, lalu kirim 1 pesan lagi.
- Kalau bot pernah pakai webhook, hapus dulu: `/deleteWebhook`.

Cara B — bot helper:
- Tambahkan **@RawDataBot** atau **@getidsbot** ke grup sementara → kirim pesan → bot akan balas `chat_id`.

### 4) Gunakan Chat ID di n8n
- Isi `TELEGRAM_CHAT_ID` (String) dengan **-100…** di Set (Config) atau lewat env.
- Pastikan node Telegram menggunakan Chat ID itu.
