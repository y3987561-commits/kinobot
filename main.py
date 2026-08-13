import asyncio, logging, os, threading
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import (
    init, save_user, get_user, ban, unban, all_users,
    stats, add_movie, get_by_code, search, delete_movie,
    toggle_like, is_liked, get_by_id, top_movies
)

load_dotenv()
TOKEN    = os.getenv("BOT_TOKEN")
ADMINS   = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
PORT     = int(os.getenv("PORT", 8080))

# ── States ────────────────────────────────────────────────
class Add(StatesGroup):
    type = State(); title = State(); code = State()
    year = State(); genre = State(); duration = State()
    desc = State(); poster = State(); file = State()

class Broadcast(StatesGroup):
    msg = State()

# ── Bot ───────────────────────────────────────────────────
bot = Bot(token=TOKEN, parse_mode="HTML")
dp  = Dispatcher(storage=MemoryStorage())

def is_admin(uid): return uid in ADMINS

# ── Keyboards ─────────────────────────────────────────────
def main_kb(uid):
    if is_admin(uid):
        return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
            [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="➕ Serial qo'shish")],
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="🏆 Top kinolar")],
        ])
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="🔍 Qidirish"), KeyboardButton(text="🏆 Top kinolar")],
    ])

def movie_kb(movie, uid):
    mid   = movie[0]
    code  = movie[2]
    liked = is_liked(uid, mid)
    heart = "❤️" if liked else "🤍"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{heart} Yoqdi ({movie[12]})", callback_data=f"like:{mid}:{uid}"),
         InlineKeyboardButton(text="📤 Ulashish", switch_inline_query=f"{code}")],
    ])

def search_results_kb(results):
    buttons = []
    for m in results:
        emoji = "🎬" if m[5] == "movie" else "📺"
        buttons.append([InlineKeyboardButton(text=f"{emoji} {m[1]} ({m[6]})", callback_data=f"get:{m[2]}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_kb(code):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"delconfirm:{code}"),
         InlineKeyboardButton(text="❌ Bekor", callback_data="delcancel")]
    ])

# ── Movie card ────────────────────────────────────────────
def movie_caption(m):
    emoji = "🎬" if m[5] == "movie" else "📺"
    text  = f"{emoji} <b>{m[1]}</b>\n\n"
    if m[6]:  text += f"📅 <b>Yil:</b> {m[6]}\n"
    if m[7]:  text += f"🎭 <b>Janr:</b> {m[7]}\n"
    if m[8]:  text += f"⏱ <b>Davomiylik:</b> {m[8]}\n"
    if m[9]:  text += f"\n📝 {m[9]}\n"
    text += f"\n👁 Ko'rishlar: <b>{m[11]}</b>  ❤️ <b>{m[12]}</b>"
    text += f"\n\n🔑 Kod: <code>{m[2]}</code>"
    return text

# ── /start ────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: types.Message):
    u = msg.from_user
    save_user(u.id, u.username, u.full_name)
    db_u = get_user(u.id)
    if db_u and db_u[4]:
        await msg.answer("🚫 Siz bloklangansiz.")
        return
    if is_admin(u.id):
        text = (f"👑 <b>Admin paneli</b>\n\n"
                f"Salom, <b>{u.first_name}</b>!\n"
                f"Bot boshqaruviga xush kelibsiz.")
    else:
        text = (f"🎬 <b>Kino botiga xush kelibsiz!</b>\n\n"
                f"Salom, <b>{u.first_name}</b>!\n\n"
                f"Kino kodini yuboring yoki 🔍 Qidirish tugmasini bosing.")
    await msg.answer(text, reply_markup=main_kb(u.id))

# ── Search ────────────────────────────────────────────────
@dp.message(F.text == "🔍 Qidirish")
async def search_trigger(msg: types.Message):
    await msg.answer("🔍 <b>Qidiruv</b>\n\nKino nomi yoki kodini yuboring:")

@dp.message(F.text == "🏆 Top kinolar")
async def top_handler(msg: types.Message):
    movies = top_movies(5)
    if not movies:
        await msg.answer("Hozircha kinolar yo'q.")
        return
    text = "🏆 <b>Eng ko'p ko'rilgan kinolar:</b>\n\n"
    for i, m in enumerate(movies, 1):
        emoji = "🎬" if m[5] == "movie" else "📺"
        text += f"{i}. {emoji} <b>{m[1]}</b> — <code>{m[2]}</code> 👁 {m[11]}\n"
    await msg.answer(text)

# ── Callback: get movie by code ───────────────────────────
@dp.callback_query(F.data.startswith("get:"))
async def cb_get(cb: types.CallbackQuery):
    code = cb.data.split(":")[1]
    await send_movie(cb.message, code, cb.from_user.id, edit=False)
    await cb.answer()

# ── Like ──────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("like:"))
async def cb_like(cb: types.CallbackQuery):
    _, mid, uid = cb.data.split(":")
    mid = int(mid); uid = int(uid)
    if cb.from_user.id != uid:
        await cb.answer("Bu tugma siz uchun emas!", show_alert=True)
        return
    liked = toggle_like(uid, mid)
    m = get_by_id(mid)
    if not m:
        await cb.answer(); return
    heart = "❤️" if liked else "🤍"
    new_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{heart} Yoqdi ({m[12]})", callback_data=f"like:{mid}:{uid}"),
         InlineKeyboardButton(text="📤 Ulashish", switch_inline_query=f"{m[2]}")],
    ])
    try:
        await cb.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass
    await cb.answer("❤️ Yoqdi!" if liked else "💔 Olib tashlandi")

# ── Delete confirm ────────────────────────────────────────
@dp.callback_query(F.data.startswith("delconfirm:"))
async def cb_delconfirm(cb: types.CallbackQuery):
    if not is_admin(cb.from_user.id): return
    code = cb.data.split(":")[1]
    delete_movie(code)
    await cb.message.edit_text(f"🗑 <code>{code}</code> o'chirildi.")
    await cb.answer("O'chirildi!")

@dp.callback_query(F.data == "delcancel")
async def cb_delcancel(cb: types.CallbackQuery):
    await cb.message.edit_text("❌ Bekor qilindi.")
    await cb.answer()

# ── Send movie ────────────────────────────────────────────
async def send_movie(msg, code, uid, edit=False):
    m = get_by_code(code)
    if not m:
        await msg.answer("❌ <b>Kino topilmadi.</b>\n\nKodni to'g'ri kiritdingizmi?")
        return
    caption = movie_caption(m)
    kb      = movie_kb(m, uid)
    if m[3]:  # poster bor
        try:
            await msg.answer_photo(photo=m[3], caption=caption, reply_markup=kb)
            await bot.send_document(msg.chat.id, document=m[4],
                                    caption=f"🎬 <b>{m[1]}</b> — yuklab olish")
            return
        except Exception:
            pass
    # fayl yuborish
    try:
        await msg.answer_video(m[4], caption=caption, reply_markup=kb)
    except Exception:
        try:
            await msg.answer_document(m[4], caption=caption, reply_markup=kb)
        except Exception:
            await msg.answer(caption + f"\n\n🔗 {m[4]}", reply_markup=kb)

# ── Admin: qo'shish ───────────────────────────────────────
@dp.message(F.text.in_(["➕ Kino qo'shish", "➕ Serial qo'shish"]))
async def add_start(msg: types.Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    mtype = "movie" if "Kino" in msg.text else "serial"
    await state.update_data(type=mtype)
    await state.set_state(Add.title)
    emoji = "🎬" if mtype == "movie" else "📺"
    await msg.answer(f"{emoji} <b>Nomi:</b>", reply_markup=types.ReplyKeyboardRemove())

@dp.message(Add.title)
async def add_title(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await state.set_state(Add.code)
    await msg.answer("🔑 <b>Kod</b> (masalan: KN001):")

@dp.message(Add.code)
async def add_code(msg: types.Message, state: FSMContext):
    await state.update_data(code=msg.text.upper())
    await state.set_state(Add.year)
    await msg.answer("📅 <b>Yil</b> (masalan: 2024):")

@dp.message(Add.year)
async def add_year(msg: types.Message, state: FSMContext):
    await state.update_data(year=msg.text)
    await state.set_state(Add.genre)
    await msg.answer("🎭 <b>Janr</b> (masalan: Drama, Komediya):")

@dp.message(Add.genre)
async def add_genre(msg: types.Message, state: FSMContext):
    await state.update_data(genre=msg.text)
    await state.set_state(Add.duration)
    data = await state.get_data()
    hint = "Davomiylik (masalan: 2s 15d)" if data['type'] == 'movie' else "Fasl/Qism (masalan: 1-fasl 5-qism)"
    await msg.answer(f"⏱ <b>{hint}:</b>")

@dp.message(Add.duration)
async def add_duration(msg: types.Message, state: FSMContext):
    await state.update_data(duration=msg.text)
    await state.set_state(Add.desc)
    await msg.answer("📝 <b>Qisqacha tavsif</b> (yoki /skip):")

@dp.message(Add.desc)
async def add_desc(msg: types.Message, state: FSMContext):
    desc = "" if msg.text == "/skip" else msg.text
    await state.update_data(desc=desc)
    await state.set_state(Add.poster)
    await msg.answer("🖼 <b>Poster</b> (rasm yuboring yoki /skip):")

@dp.message(Add.poster)
async def add_poster(msg: types.Message, state: FSMContext):
    poster_id = ""
    if msg.photo:
        poster_id = msg.photo[-1].file_id
    await state.update_data(poster=poster_id)
    await state.set_state(Add.file)
    await msg.answer("📁 <b>Kino faylini yuboring:</b>")

@dp.message(Add.file)
async def add_file(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = (msg.video.file_id if msg.video else
               msg.document.file_id if msg.document else msg.text)
    ok = add_movie(
        data['title'], data['code'], file_id, data['poster'],
        data['type'], data['year'], data['genre'], data['duration'], data['desc']
    )
    await state.clear()
    if ok:
        emoji = "🎬" if data['type'] == 'movie' else "📺"
        text = (f"✅ <b>Qo'shildi!</b>\n\n"
                f"{emoji} <b>{data['title']}</b>\n"
                f"🔑 Kod: <code>{data['code']}</code>\n"
                f"📅 {data['year']} | 🎭 {data['genre']}\n"
                f"⏱ {data['duration']}")
        await msg.answer(text, reply_markup=main_kb(msg.from_user.id))
    else:
        await msg.answer("❌ Bu kod allaqachon mavjud!", reply_markup=main_kb(msg.from_user.id))

# ── Admin: statistika ─────────────────────────────────────
@dp.message(F.text == "📊 Statistika")
async def cmd_stats(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    total, active, banned_c, movies, serial, views = stats()
    await msg.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"✅ Faol: <b>{active}</b>\n"
        f"🚫 Bloklangan: <b>{banned_c}</b>\n\n"
        f"🎬 Kinolar: <b>{movies}</b>\n"
        f"📺 Seriallar: <b>{serial}</b>\n"
        f"👁 Jami ko'rishlar: <b>{views}</b>"
    )

# ── Admin: foydalanuvchilar ───────────────────────────────
@dp.message(F.text == "👥 Foydalanuvchilar")
async def cmd_users(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    await msg.answer(
        "👥 <b>Foydalanuvchi boshqaruvi</b>\n\n"
        "/ban &lt;id&gt; — bloklash\n"
        "/unban &lt;id&gt; — blokdan chiqarish\n"
        "/userinfo &lt;id&gt; — ma'lumot\n"
        "/del &lt;kod&gt; — kino o'chirish"
    )

@dp.message(Command("ban"))
async def cmd_ban(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: await msg.answer("Foydalanish: /ban &lt;id&gt;"); return
    try:
        uid = int(parts[1]); ban(uid)
        await msg.answer(f"🚫 <code>{uid}</code> bloklandi.")
        try: await bot.send_message(uid, "🚫 Siz botdan bloklangansiz.")
        except: pass
    except: await msg.answer("❌ Xatolik")

@dp.message(Command("unban"))
async def cmd_unban(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: await msg.answer("Foydalanish: /unban &lt;id&gt;"); return
    try:
        uid = int(parts[1]); unban(uid)
        await msg.answer(f"✅ <code>{uid}</code> blokdan chiqarildi.")
        try: await bot.send_message(uid, "✅ Blokdan chiqarildingiz.")
        except: pass
    except: await msg.answer("❌ Xatolik")

@dp.message(Command("userinfo"))
async def cmd_userinfo(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: await msg.answer("Foydalanish: /userinfo &lt;id&gt;"); return
    try:
        u = get_user(int(parts[1]))
        if u:
            await msg.answer(
                f"👤 ID: <code>{u[0]}</code>\n"
                f"🔗 @{u[1] or 'Yoq'}\n"
                f"📝 {u[2]}\n"
                f"📅 {u[3]}\n"
                f"🚫 Bloklangan: {'Ha' if u[4] else 'Yoq'}"
            )
        else: await msg.answer("❌ Topilmadi.")
    except: await msg.answer("❌ Xatolik")

@dp.message(Command("del"))
async def cmd_del(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    parts = msg.text.split()
    if len(parts) < 2: await msg.answer("Foydalanish: /del &lt;kod&gt;"); return
    code = parts[1].upper()
    await msg.answer(f"🗑 <code>{code}</code> ni o'chirishni tasdiqlaysizmi?",
                     reply_markup=confirm_kb(code))

# ── Admin: broadcast ──────────────────────────────────────
@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(msg: types.Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await state.set_state(Broadcast.msg)
    await msg.answer("📢 Xabarni yuboring (/cancel — bekor):",
                     reply_markup=types.ReplyKeyboardRemove())

@dp.message(Command("cancel"))
async def cmd_cancel(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ Bekor qilindi.", reply_markup=main_kb(msg.from_user.id))

@dp.message(Broadcast.msg)
async def broadcast_do(msg: types.Message, state: FSMContext):
    await state.clear()
    users = all_users()
    sent = failed = 0
    status = await msg.answer(f"📢 {len(users)} ta foydalanuvchiga yuborilmoqda...")
    for u in users:
        try:
            await bot.copy_message(u[0], msg.chat.id, msg.message_id)
            sent += 1
        except: failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ Tugadi!\n\n✅ {sent} ta yuborildi\n❌ {failed} ta xatolik")
    await msg.answer("Davom etish:", reply_markup=main_kb(msg.from_user.id))

# ── Text handler ──────────────────────────────────────────
SKIP = {"➕ Kino qo'shish","➕ Serial qo'shish","👥 Foydalanuvchilar",
        "📊 Statistika","📢 Xabar yuborish","🏆 Top kinolar","🔍 Qidirish"}

@dp.message(F.text)
async def handle_text(msg: types.Message, state: FSMContext):
    if msg.text in SKIP: return
    if await state.get_state(): return
    uid   = msg.from_user.id
    query = msg.text.strip()

    # Aniq kod
    m = get_by_code(query)
    if m:
        await send_movie(msg, query, uid)
        return

    # Qidiruv
    results = search(query)
    if results:
        if len(results) == 1:
            await send_movie(msg, results[0][2], uid)
        else:
            await msg.answer(
                f"🔍 <b>{len(results)} ta natija topildi:</b>",
                reply_markup=search_results_kb(results)
            )
    else:
        await msg.answer(
            "❌ <b>Kino topilmadi.</b>\n\n"
            "Kodni yoki nomni to'g'ri kiriting.\n"
            "Masalan: <code>KN001</code>"
        )

# ── Flask (ping) ──────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Bot ishlayapti!", 200

# ── Main ──────────────────────────────────────────────────
async def main():
    init()
    logging.basicConfig(level=logging.WARNING)
    t = threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=PORT, use_reloader=False),
        daemon=True
    )
    t.start()
    print(f"✅ Flask port {PORT}")
    print("🤖 Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
