"""
ربات ایموجی پرمیوم - نسخه پایتون (Polling)
مناسب Railway / VPS
توکن از محیط | ادمین: 6691993264 | جوین اجباری: @SELF_MR0
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
import aiosqlite
import asyncio

# ──────────────────────────── تنظیمات ────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6691993264"))
DEFAULT_FORCE_CHANNEL = "@SELF_MR0"
EMOJI_REFERENCE_CHANNEL = "@CustomEmojiPack"
DONATE_URL = "https://t.me/SikoTMT"
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN تنظیم نشده!")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ──────────────────────────── متن‌ها ────────────────────────────
T = {
    "welcome": "🔸 <b>خوش اومدی به ربات ایموجی پرمیوم</b>\n\nیکی از گزینه‌های زیر رو انتخاب کن 🔸",
    "ad_once": "🔔 ربات‌های کاربردی و رایگان بیشتری در کانالم هست\n👉 @sikotmt عضو بشید",
    "register_instructions": (
        "🔸 <b>ثبت کانال جدید</b>\n\n"
        "1️⃣ ربات رو توی کانالت <b>ادمین</b> کن و دسترسی «ارسال پیام» رو بهش بده\n"
        "2️⃣ یه پست از همون کانال رو برای ربات <b>فوروارد</b> کن"
    ),
    "register_force_instructions": (
        "🔸 <b>افزودن کانال جوین اجباری</b>\n\n"
        "1️⃣ ربات رو توی کانال/گروه عضو یا ادمین کن\n"
        "2️⃣ یه پست از همون کانال/گروه رو برای ربات <b>فوروارد</b> کن"
    ),
    "no_channels": "❗️ هنوز هیچ کانالی ثبت نکردی. اول از «ثبت کانال» استفاده کن.",
    "choose_channel": "کانالی که می‌خوای پست توش ارسال بشه رو انتخاب کن:",
    "choose_post_type": "نوع پستت رو انتخاب کن:",
    "ask_text": (
        f"📝 <b>متن پستت رو بنویس</b>\n\n"
        f"مثال: سلام [5417984163095542602]\n\n"
        f"برای ایموجی پرمیوم، آیدی عددیش رو داخل [ ] بنویس.\n"
        f"آیدی‌ها رو از کانال {EMOJI_REFERENCE_CHANNEL} بردار."
    ),
    "ask_caption": "می‌خوای براش کپشن بذاری؟ متنش رو بفرست، یا بنویس «بدون کپشن».",
    "preview_header": "🔎 <b>پیش‌نمایش پستت</b> 👇 آیا همین ارسال بشه؟",
    "sent_ok": "✅ پست با موفقیت ارسال شد 🔸",
    "cancelled": "❌ ارسال لغو شد.",
    "support": (
        f"🛟 <b>راهنما</b>\n\n"
        f"1️⃣ ثبت کانال: ربات رو ادمین کن و یه پست فوروارد کن.\n"
        f"2️⃣ ارسال پست: از منو «ارسال پست» رو بزن.\n"
        f"3️⃣ آیدی ایموجی پرمیوم از کانال {EMOJI_REFERENCE_CHANNEL}\n\n"
        f"پشتیبانی: @sikotmt"
    ),
    "donate_intro": "با دونیت شما اشتراک پرمیوم ربات تمدید می‌شه.\n\nاز همراهیت ممنونیم 🙏",
    "denied": "⛔️ ربات خصوصیه و فقط سازنده دسترسی داره.",
    "generic_error": "❗️ یه خطایی پیش اومد. دوباره امتحان کن.",
    "must_join": "⛔️ <b>برای استفاده باید عضو کانال‌های زیر بشی</b>\n\nبعد از عضویت دکمه «بررسی مجدد» رو بزن.",
    "still_not_member": "❗️ هنوز عضو همه‌شون نشدی.",
    "joined_ok": "✅ عضویت تایید شد، خوش اومدی!",
}

COLOR = ["✦", "✧", "✦"]

def cl(i: int, t: str) -> str:
    return f"{COLOR[i % 3]} {t}"

def esc(t: str) -> str:
    return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ──────────────────────────── دیتابیس ────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                username TEXT,
                owner_id INTEGER,
                added_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'idle',
                context TEXT,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS setup_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS bot_users (
                user_id INTEGER PRIMARY KEY,
                welcomed INTEGER NOT NULL DEFAULT 0,
                joined_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS force_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                username TEXT,
                invite_link TEXT,
                added_at INTEGER NOT NULL
            );
        """)
        await db.commit()

async def get_setting(key: str, default=None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM setup_meta WHERE key=?", (key,)) as c:
            row = await c.fetchone()
            return row[0] if row else default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO setup_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        await db.commit()

async def get_mode() -> str:
    m = await get_setting("bot_mode", "private")
    return "public" if m == "public" else "private"

async def ensure_user(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT welcomed FROM bot_users WHERE user_id=?", (uid,)) as c:
            row = await c.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO bot_users(user_id,welcomed,joined_at) VALUES(?,0,?)",
                (uid, int(datetime.now().timestamp()*1000))
            )
            await db.commit()
            return 0
        return row[0]

async def mark_welcomed(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bot_users SET welcomed=1 WHERE user_id=?", (uid,))
        await db.commit()

async def get_session(uid: int) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT state, context FROM sessions WHERE user_id=?", (uid,)) as c:
            row = await c.fetchone()
    if not row:
        return {"state": "idle", "context": {}}
    try:
        ctx = json.loads(row[1]) if row[1] else {}
    except:
        ctx = {}
    return {"state": row[0], "context": ctx}

async def set_session(uid: int, state: str, context: dict = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO sessions(user_id,state,context,updated_at) VALUES(?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET state=excluded.state, context=excluded.context, updated_at=excluded.updated_at""",
            (uid, state, json.dumps(context or {}), int(datetime.now().timestamp()*1000))
        )
        await db.commit()

async def clear_session(uid: int):
    await set_session(uid, "idle", {})

async def list_channels(owner_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, chat_id, title, username FROM channels WHERE owner_id=? ORDER BY added_at",
            (owner_id,)
        ) as c:
            rows = await c.fetchall()
    return [{"id": r[0], "chat_id": r[1], "title": r[2], "username": r[3]} for r in rows]

async def get_channel(cid: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, chat_id, title, username, owner_id FROM channels WHERE id=?", (cid,)
        ) as c:
            r = await c.fetchone()
    if not r:
        return None
    return {"id": r[0], "chat_id": r[1], "title": r[2], "username": r[3], "owner_id": r[4]}

async def upsert_channel(chat_id: int, title: str, username: str, owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO channels(chat_id,title,username,owner_id,added_at) VALUES(?,?,?,?,?)
               ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, username=excluded.username, owner_id=excluded.owner_id""",
            (chat_id, title, username, owner_id, int(datetime.now().timestamp()*1000))
        )
        await db.commit()

async def list_force() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, chat_id, title, username, invite_link FROM force_channels ORDER BY added_at"
        ) as c:
            rows = await c.fetchall()
    return [{"id": r[0], "chat_id": r[1], "title": r[2], "username": r[3], "invite_link": r[4]} for r in rows]

async def add_force(chat_id: int, title: str, username: str, invite: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO force_channels(chat_id,title,username,invite_link,added_at) VALUES(?,?,?,?,?)
               ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, username=excluded.username, invite_link=excluded.invite_link""",
            (chat_id, title, username, invite, int(datetime.now().timestamp()*1000))
        )
        await db.commit()

async def del_force(fid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM force_channels WHERE id=?", (fid,))
        await db.commit()

async def ensure_default_force():
    try:
        channels = await list_force()
        if any((c.get("username") or "").lower() == "self_mr0" for c in channels):
            return
        chat = await bot.get_chat(DEFAULT_FORCE_CHANNEL)
        invite = None
        if not chat.username:
            try:
                invite = await bot.export_chat_invite_link(chat.id)
            except:
                pass
        await add_force(chat.id, chat.title or "SELF_MR0", chat.username or "SELF_MR0", invite)
        logger.info("کانال جوین اجباری پیش‌فرض اضافه شد: %s", DEFAULT_FORCE_CHANNEL)
    except Exception as e:
        logger.warning("نتونست کانال پیش‌فرض رو اضافه کنه: %s", e)

async def check_force(uid: int) -> Dict:
    channels = await list_force()
    if not channels:
        return {"ok": True, "missing": []}
    missing = []
    for ch in channels:
        try:
            m = await bot.get_chat_member(ch["chat_id"], uid)
            if m.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
                missing.append(ch)
        except:
            missing.append(ch)
    return {"ok": len(missing) == 0, "missing": missing}

# ──────────────────────────── کیبوردها ────────────────────────────
def main_kb(is_admin: bool):
    rows = [
        [InlineKeyboardButton(text=cl(0, "ارسال پست ✍️"), callback_data="menu:send"),
         InlineKeyboardButton(text=cl(1, "ثبت کانال ☸️"), callback_data="menu:register")],
        [InlineKeyboardButton(text=cl(2, "پشتیبانی 🛟"), callback_data="menu:support"),
         InlineKeyboardButton(text=cl(0, "حمایت 💎"), callback_data="menu:donate")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text=cl(1, "تنظیمات ⚙️"), callback_data="menu:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_kb(cb="nav:back"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=cl(2, "بازگشت 🔙"), callback_data=cb)]])

def post_type_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cl(0, "عکس 🖼"), callback_data="ptype:photo"),
         InlineKeyboardButton(text=cl(1, "فیلم 🎬"), callback_data="ptype:video")],
        [InlineKeyboardButton(text=cl(2, "فایل 📁"), callback_data="ptype:document"),
         InlineKeyboardButton(text=cl(0, "متن 📝"), callback_data="ptype:text")],
        [InlineKeyboardButton(text=cl(2, "بازگشت 🔙"), callback_data="nav:back")]
    ])

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cl(1, "بله، ارسال کن ✅"), callback_data="confirm:yes"),
         InlineKeyboardButton(text=cl(0, "لغو ❌"), callback_data="confirm:no")]
    ])

def must_join_kb(channels):
    rows = []
    for i, c in enumerate(channels):
        url = f"https://t.me/{c['username']}" if c.get("username") else c.get("invite_link")
        if url:
            rows.append([InlineKeyboardButton(text=cl(i, c["title"]), url=url)])
    rows.append([InlineKeyboardButton(text=cl(2, "بررسی مجدد 🔄"), callback_data="fcheck")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def settings_kb(mode: str):
    txt = "سوییچ به خصوصی 🔴" if mode == "public" else "سوییچ به عمومی 🟢"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cl(0, txt), callback_data="settings:toggle")],
        [InlineKeyboardButton(text=cl(2, "جوین اجباری 📋"), callback_data="menu:forcelist")],
        [InlineKeyboardButton(text=cl(2, "بازگشت 🔙"), callback_data="nav:back")]
    ])

def force_list_kb(channels):
    rows = []
    for i, c in enumerate(channels):
        url = f"https://t.me/{c['username']}" if c.get("username") else c.get("invite_link")
        btn = InlineKeyboardButton(text=cl(i, c["title"]), url=url) if url else InlineKeyboardButton(text=cl(i, c["title"]), callback_data="noop")
        rows.append([btn, InlineKeyboardButton(text="🗑", callback_data=f"fcdel:{c['id']}")])
    rows.append([InlineKeyboardButton(text=cl(1, "افزودن کانال ➕"), callback_data="fcadd")])
    rows.append([InlineKeyboardButton(text=cl(2, "بازگشت 🔙"), callback_data="menu:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def channel_list_kb(channels):
    rows = [[InlineKeyboardButton(text=cl(i, c["title"]), callback_data=f"pick:{c['id']}")] for i, c in enumerate(channels)]
    rows.append([InlineKeyboardButton(text=cl(2, "بازگشت 🔙"), callback_data="nav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ──────────────────────────── دسترسی ────────────────────────────
def is_admin(uid: int) -> bool:
    return int(uid) == ADMIN_ID

async def access(uid: int) -> Dict:
    mode = await get_mode()
    admin = is_admin(uid)
    await ensure_user(uid)
    if mode == "private" and not admin:
        return {"ok": False, "admin": admin, "mode": mode}
    return {"ok": True, "admin": admin, "mode": mode}

# ──────────────────────────── هندلرها ────────────────────────────
@dp.message(CommandStart())
async def start(msg: Message):
    uid = msg.from_user.id
    acc = await access(uid)
    if not acc["ok"]:
        await msg.answer(T["denied"])
        return

    await clear_session(uid)
    welcomed = await ensure_user(uid)
    if welcomed == 0:
        await msg.answer(T["ad_once"])
        await mark_welcomed(uid)

    if acc["mode"] == "public" and not acc["admin"]:
        sub = await check_force(uid)
        if not sub["ok"]:
            await msg.answer(T["must_join"], reply_markup=must_join_kb(sub["missing"]))
            return

    await msg.answer(T["welcome"], reply_markup=main_kb(acc["admin"]))

@dp.message(F.forward_from_chat | F.forward_origin)
async def on_forward(msg: Message):
    uid = msg.from_user.id
    sess = await get_session(uid)
    state = sess["state"]

    if state == "awaiting_channel":
        await do_register_channel(msg)
    elif state == "awaiting_force":
        await do_register_force(msg)

async def do_register_channel(msg: Message):
    uid = msg.from_user.id
    origin = msg.forward_from_chat or (msg.forward_origin.chat if msg.forward_origin and hasattr(msg.forward_origin, "chat") else None)
    if not origin or origin.type not in ("channel", "supergroup"):
        await msg.answer("❗️ این پیام از کانال فوروارد نشده.", reply_markup=back_kb())
        return

    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(origin.id, me.id)
        can_post = member.status == ChatMemberStatus.ADMINISTRATOR and getattr(member, "can_post_messages", False)
        if not can_post:
            await msg.answer("❗️ ربات دسترسی ارسال پیام نداره. دسترسی بده و دوباره فوروارد کن.", reply_markup=back_kb())
            return
    except Exception:
        await msg.answer("❗️ ربات هنوز ادمین این کانال نیست.", reply_markup=back_kb())
        return

    await upsert_channel(origin.id, origin.title or "بدون نام", origin.username, uid)
    await clear_session(uid)
    acc = await access(uid)
    await msg.answer(
        f"🏵 کانال <b>{esc(origin.title)}</b> با موفقیت ثبت شد ✅",
        reply_markup=main_kb(acc["admin"])
    )

async def do_register_force(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        return
    origin = msg.forward_from_chat or (msg.forward_origin.chat if msg.forward_origin and hasattr(msg.forward_origin, "chat") else None)
    if not origin:
        await msg.answer("❗️ پیام فوروارد نشده.", reply_markup=back_kb("menu:forcelist"))
        return

    invite = None
    if not origin.username:
        try:
            invite = await bot.export_chat_invite_link(origin.id)
        except:
            pass
    await add_force(origin.id, origin.title or "بدون نام", origin.username, invite)
    await clear_session(uid)
    await msg.answer(f"✅ کانال «{esc(origin.title)}» به جوین اجباری اضافه شد.", reply_markup=back_kb("menu:forcelist"))

@dp.message(F.text)
async def on_text(msg: Message):
    uid = msg.from_user.id
    acc = await access(uid)
    if not acc["ok"]:
        await msg.answer(T["denied"])
        return

    if acc["mode"] == "public" and not acc["admin"]:
        sub = await check_force(uid)
        if not sub["ok"]:
            await msg.answer(T["must_join"], reply_markup=must_join_kb(sub["missing"]))
            return

    sess = await get_session(uid)
    state = sess["state"]
    ctx = sess["context"]

    if state == "awaiting_text":
        ctx["text"] = msg.text
        await go_preview(msg, uid, ctx)
    elif state == "awaiting_caption":
        if msg.text.strip() != "بدون کپشن":
            ctx["caption"] = msg.text
        await go_preview(msg, uid, ctx)
    else:
        await msg.answer(T["welcome"], reply_markup=main_kb(acc["admin"]))

@dp.message(F.photo | F.video | F.document)
async def on_media(msg: Message):
    uid = msg.from_user.id
    sess = await get_session(uid)
    if sess["state"] != "awaiting_media":
        return

    ctx = sess["context"]
    ptype = ctx.get("post_type")
    file_id = None
    if ptype == "photo" and msg.photo:
        file_id = msg.photo[-1].file_id
    elif ptype == "video" and msg.video:
        file_id = msg.video.file_id
    elif ptype == "document" and msg.document:
        file_id = msg.document.file_id

    if not file_id:
        await msg.answer("❗️ فایل معتبر نیست. دوباره بفرست.", reply_markup=back_kb())
        return

    ctx["file_id"] = file_id
    await set_session(uid, "awaiting_caption", ctx)
    await msg.answer(T["ask_caption"], reply_markup=back_kb())

async def go_preview(msg: Message, uid: int, ctx: dict):
    ptype = ctx.get("post_type")
    text = ctx.get("text") if ptype == "text" else ctx.get("caption")
    await set_session(uid, "awaiting_confirm", ctx)

    await msg.answer(T["preview_header"])
    try:
        if ptype == "text":
            sent = await bot.send_message(msg.chat.id, text or "-", disable_web_page_preview=True)
        elif ptype == "photo":
            sent = await bot.send_photo(msg.chat.id, ctx["file_id"], caption=text)
        elif ptype == "video":
            sent = await bot.send_video(msg.chat.id, ctx["file_id"], caption=text)
        else:
            sent = await bot.send_document(msg.chat.id, ctx["file_id"], caption=text)

        ctx["preview_chat"] = msg.chat.id
        ctx["preview_msg"] = sent.message_id
        await set_session(uid, "awaiting_confirm", ctx)
        await msg.answer("تایید می‌کنی؟", reply_markup=confirm_kb())
    except Exception as e:
        logger.error("preview error: %s", e)
        await msg.answer(T["generic_error"], reply_markup=back_kb())

@dp.callback_query()
async def on_callback(cb: CallbackQuery):
    uid = cb.from_user.id
    data = cb.data or ""
    acc = await access(uid)

    if not acc["ok"]:
        await cb.answer(T["denied"], show_alert=True)
        return

    await cb.answer()

    if data == "fcheck":
        sub = await check_force(uid)
        if sub["ok"]:
            await cb.message.edit_text(T["joined_ok"] + "\n\n" + T["welcome"], reply_markup=main_kb(acc["admin"]))
        else:
            await cb.answer(T["still_not_member"], show_alert=True)
        return

    if acc["mode"] == "public" and not acc["admin"]:
        sub = await check_force(uid)
        if not sub["ok"]:
            await cb.message.edit_text(T["must_join"], reply_markup=must_join_kb(sub["missing"]))
            return

    if data == "nav:back":
        await clear_session(uid)
        await cb.message.edit_text(T["welcome"], reply_markup=main_kb(acc["admin"]))
        return

    if data.startswith("menu:"):
        await handle_menu(data.split(":")[1], cb, acc)
    elif data.startswith("ptype:"):
        await handle_ptype(data.split(":")[1], cb)
    elif data.startswith("pick:"):
        await handle_pick(data.split(":")[1], cb)
    elif data.startswith("confirm:"):
        await handle_confirm(data.split(":")[1], cb, acc)
    elif data.startswith("settings:"):
        await handle_settings(data.split(":")[1], cb, acc)
    elif data.startswith("fcdel:"):
        await handle_fcdel(data.split(":")[1], cb, acc)
    elif data == "fcadd":
        if acc["admin"]:
            await set_session(uid, "awaiting_force", {})
            await cb.message.edit_text(T["register_force_instructions"], reply_markup=back_kb("menu:forcelist"))

async def handle_menu(param: str, cb: CallbackQuery, acc: Dict):
    uid = cb.from_user.id
    if param == "register":
        await set_session(uid, "awaiting_channel", {})
        await cb.message.edit_text(T["register_instructions"], reply_markup=back_kb())
    elif param == "send":
        channels = await list_channels(uid)
        if not channels:
            await cb.message.edit_text(T["no_channels"], reply_markup=back_kb())
            return
        if len(channels) == 1:
            ctx = {"channel_id": channels[0]["id"], "channel_chat": channels[0]["chat_id"]}
            await set_session(uid, "awaiting_ptype", ctx)
            await cb.message.edit_text(T["choose_post_type"], reply_markup=post_type_kb())
        else:
            await cb.message.edit_text(T["choose_channel"], reply_markup=channel_list_kb(channels))
    elif param == "support":
        await cb.message.edit_text(T["support"], reply_markup=back_kb())
    elif param == "donate":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cl(1, "دونیت 💎"), url=DONATE_URL)],
            [InlineKeyboardButton(text=cl(2, "بازگشت 🔙"), callback_data="nav:back")]
        ])
        await cb.message.edit_text(T["donate_intro"], reply_markup=kb)
    elif param == "settings":
        if not acc["admin"]:
            return
        mode = await get_mode()
        await cb.message.edit_text(
            f"⚙️ <b>تنظیمات</b>\n\nحالت فعلی: {'🟢 عمومی' if mode == 'public' else '🔴 خصوصی'}",
            reply_markup=settings_kb(mode)
        )
    elif param == "forcelist":
        if not acc["admin"]:
            return
        channels = await list_force()
        await cb.message.edit_text(
            f"📋 <b>جوین اجباری</b> ({len(channels)})",
            reply_markup=force_list_kb(channels)
        )

async def handle_ptype(ptype: str, cb: CallbackQuery):
    uid = cb.from_user.id
    sess = await get_session(uid)
    ctx = {**sess["context"], "post_type": ptype}
    if ptype == "text":
        await set_session(uid, "awaiting_text", ctx)
        await cb.message.edit_text(T["ask_text"], reply_markup=back_kb())
    else:
        await set_session(uid, "awaiting_media", ctx)
        labels = {"photo": "عکس", "video": "فیلم", "document": "فایل"}
        await cb.message.edit_text(f"لطفاً <b>{labels.get(ptype)}</b> رو بفرست:", reply_markup=back_kb())

async def handle_pick(cid: str, cb: CallbackQuery):
    uid = cb.from_user.id
    ch = await get_channel(int(cid))
    if not ch or ch["owner_id"] != uid:
        await cb.message.edit_text(T["generic_error"], reply_markup=back_kb())
        return
    ctx = {"channel_id": ch["id"], "channel_chat": ch["chat_id"]}
    await set_session(uid, "awaiting_ptype", ctx)
    await cb.message.edit_text(T["choose_post_type"], reply_markup=post_type_kb())

async def handle_confirm(param: str, cb: CallbackQuery, acc: Dict):
    uid = cb.from_user.id
    sess = await get_session(uid)
    ctx = sess["context"]

    if param == "no":
        await clear_session(uid)
        await cb.message.edit_text(T["cancelled"], reply_markup=main_kb(acc["admin"]))
        return

    ch = await get_channel(ctx.get("channel_id"))
    if not ch or ch["owner_id"] != uid:
        await cb.message.edit_text("❗️ کانال پیدا نشد.", reply_markup=main_kb(acc["admin"]))
        await clear_session(uid)
        return

    try:
        await bot.forward_message(
            chat_id=ch["chat_id"],
            from_chat_id=ctx["preview_chat"],
            message_id=ctx["preview_msg"]
        )
        await clear_session(uid)
        await cb.message.edit_text(T["sent_ok"], reply_markup=main_kb(acc["admin"]))
    except Exception as e:
        logger.error("send error: %s", e)
        await cb.message.edit_text("❗️ خطا در ارسال. دسترسی ربات رو چک کن.", reply_markup=main_kb(acc["admin"]))

async def handle_settings(param: str, cb: CallbackQuery, acc: Dict):
    if not acc["admin"]:
        return
    if param == "toggle":
        current = await get_mode()
        new = "private" if current == "public" else "public"
        await set_setting("bot_mode", new)
        await cb.message.edit_text(
            f"⚙️ <b>تنظیمات</b>\n\nحالت فعلی: {'🟢 عمومی' if new == 'public' else '🔴 خصوصی'}",
            reply_markup=settings_kb(new)
        )

async def handle_fcdel(fid: str, cb: CallbackQuery, acc: Dict):
    if not acc["admin"]:
        return
    await del_force(int(fid))
    channels = await list_force()
    await cb.message.edit_text(f"🗑 حذف شد\n\n📋 جوین اجباری ({len(channels)})", reply_markup=force_list_kb(channels))

# ──────────────────────────── اجرا ────────────────────────────
async def main():
    await init_db()
    await ensure_default_force()
    logger.info("ربات شروع به کار کرد | ادمین: %s", ADMIN_ID)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
