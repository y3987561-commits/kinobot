# 🎬 KinoBot

Telegram kino boti — Railway'da ishlaydigan professional bot.

## Funksiyalar

### 👤 Foydalanuvchi
- Kino kodi orqali qidirish (masalan: `KN001`)
- Nom bo'yicha qidirish
- 🏆 Top 5 eng ko'p ko'rilgan kinolar
- ❤️ Like/Dislike tizimi
- 📤 Kino havolasini ulashish

### 👑 Admin
- ➕ Kino va serial qo'shish (poster, fayl, tavsif bilan)
- 🗑 Kino o'chirish (tasdiqlash bilan)
- 📊 Statistika (foydalanuvchilar, ko'rishlar)
- 👥 Foydalanuvchi boshqaruvi (ban/unban)
- 📢 Barcha foydalanuvchilarga xabar yuborish

## O'rnatish

### Railway orqali

1. Railway'da yangi loyiha yarating
2. GitHub repo'ni ulang
3. Environment variables qo'shing:
   - `BOT_TOKEN` — Telegram bot tokeni
   - `ADMIN_IDS` — Admin ID'lar (vergul bilan, masalan: `123456789,987654321`)

## Environment Variables

| O'zgaruvchi | Tavsif | Misol |
|-------------|--------|-------|
| `BOT_TOKEN` | BotFather tokeni | `1234567890:AAF...` |
| `ADMIN_IDS` | Admin user ID'lar | `7945692959` |
| `PORT` | Flask port (ixtiyoriy) | `8080` |

## Kino qo'shish

Admin klaviaturasidan:
1. `➕ Kino qo'shish` yoki `➕ Serial qo'shish` tugmasini bosing
2. Nom, kod, yil, janr, davomiylik, tavsif kiriting
3. Poster rasmini yuboring (ixtiyoriy)
4. Kino faylini yuboring (video yoki document)

Foydalanuvchilar kinoni kod orqali topadi: `KN001`
