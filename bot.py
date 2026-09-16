import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ChatMemberUpdated, FSInputFile
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.client.default import DefaultBotProperties
import aiosqlite

# ──────────────────────────── تنظیمات ────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6691993264"))
DEFAULT_FORCE_CHANNEL = "@SELF_MR0"
EMOJI_REFERENCE_CHANNEL = "@CustomEmojiPack"
DONATE_URL = "https://t.me/SikoTMT"
DB_PATH = os.getenv("DB_PATH", "bot.db")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "siko-secret-change-me")
WEBHOOK_PATH = "/webhook"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
app = FastAPI()

# ──────────────────────────── متن‌ها ────────────────────────────
T = {
    "welcome": "🔸 <b>خوش اومدی به ربات ایموجی پرمیوم</b>\n\nیکی از گزینه‌های زیر رو انتخاب کن 🔸",
    "ad_once": "🔔 ربات‌های کاربردی و رایگان بیشتری در کانالم هست\n👉 @sikotmt عضو بشید",
    "register_instructions": (
        "🔸 <b>ثبت کانال جدید</b>\n\n"
        "1️⃣ ربات رو توی کانالت <b>ادمین</b> کن و دسترسی «ارسال و مدیریت پست‌ها» رو بهش بده\n"
        "2️⃣ یه پست از همون کانال رو برای ربات <b>فوروارد</b> کن"
    ),
    "register_force_instructions": (
        "🔸 <b>افزودن کانال جوین اجباری</b>\n\n"
        "1️⃣ ربات رو توی کانال/گروه مورد نظر عضو یا ادمین کن\n"
        "2️⃣ یه پست از همون کانال/گروه رو برای ربات <b>فوروارد</b> کن"
    ),
    "no_channels": "❗️ هنوز هیچ کانالی ثبت نکردی. اول از «ثبت کانال» استفاده کن.",
    "choose_channel": "کانالی که می‌خوای پست توش ارسال بشه رو انتخاب کن:",
    "choose_post_type": "نوع پستت رو انتخاب کن:",
    "ask_text": (
        f"📝 <b>متن پستت رو بنویس</b>\n\n"
        f"مثال: سلام [5417984163095542602]\n\n"
        f"برای گذاشتن ایموجی پرمیوم، آیدی عددیش رو داخل [ ] بنویس.\n"
        f"اگه آیدی رو نمی‌دونی، از کانال {EMOJI_REFERENCE_CHANNEL} می‌تونی ببینی و برداری."
    ),
    "ask_caption": "می‌خوای براش کپشن بذاری؟ متنش رو بفرست، یا بنویس «بدون کپشن».",
    "preview_header": "🔎 <b>پیش‌نمایش پستت</b> 👇 آیا همین ارسال بشه؟",
    "sent_ok": "✅ پست با موفقیت ارسال شد 🔸",
    "cancelled": "❌ ارسال لغو شد.",
    "bad_entities": "❗️ یکی از آیدی‌های ایموجی که وارد کردی معتبر نیست، یا مشکلی در فرمت متن پیش اومد. لطفاً دوباره متن رو بفرست.",
    "support": (
        f"🛟 <b>راهنما</b>\n\n"
        f"1️⃣ برای ثبت کانال: ربات رو ادمین کانالت کن و یه پست ازش فوروارد کن.\n"
        f"2️⃣ برای ارسال پست: از منوی اصلی «ارسال پست» رو بزن و مراحل رو طی کن.\n"
        f"3️⃣ آیدی ایموجی‌های پرمیوم رو از کانال {EMOJI_REFERENCE_CHANNEL} بردار.\n\n"
        f"برای سوال بیشتر با سازنده : @sikotmt در ارتباط باش."
    ),
    "donate_intro": (
        "با دونیت و حمایت شما، اشتراک پرمیوم ربات تمدید می‌شه و همزمان روی آپدیت‌ها "
        "و امکانات ربات جدید هم کار می‌کنیم.\n\nاز همراهی و لطفت ممنونیم! 🙏"
    ),
    "donate_footer": (
        "🔴 𝖩𝗈𝗂𝗇 𝖴𝗌┊➥ https://t.me/Siko_TMT\n"
        "🔵 𝕏 𝖯𝖺𝗀𝖾┊➥ https://x.com/Siko_Tmt\n"
        "🧑‍💻 𝖢𝗈𝗇𝗍𝖺𝖼𝗍┊➥ https://t.me/SikoTMT\n\n"
        "━━━━━━━━━✦ SIKO TMT ✦━━━━━━━━━"
    ),
    "denied": "⛔️ ربات در حال حاضر خصوصیه و فقط سازنده بهش دسترسی داره.",
    "generic_error": "❗️ یه خطایی پیش اومد. دوباره امتحان کن.",
    "must_join": "⛔️ <b>برای استفاده از ربات باید عضو کانال/گروه‌های زیر بشی</b>\n\nبعد از عضویت، دکمه «بررسی مجدد» رو بزن.",
    "still_not_member": "❗️ هنوز عضو همه‌شون نشدی.",
    "joined_ok": "✅ عضویت تایید شد، خوش اومدی!",
    "force_channel_deleted": "🗑 کانال از لیست جوین اجباری حذف شد.",
}

COLOR_CYCLE = ["✦", "✧", "✦"]

def color_label(index: int, label: str) -> str:
    return f"{COLOR_CYCLE[index % len(COLOR_CYCLE)]} {label}"

def escape_html(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

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
            CREATE TABLE IF NOT EXISTS posts_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                post_type TEXT,
                sent_at INTEGER
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


async def get_setting(key: str, fallback=None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM setup_meta WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else fallback


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO setup_meta (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        await db.commit()


async def get_bot_mode() -> str:
    mode = await get_setting("bot_mode", "private")
    return "public" if mode == "public" else "private"


async def ensure_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, welcomed FROM bot_users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row:
            return {"user_id": row[0], "welcomed": row[1]}
        await db.execute(
            "INSERT INTO bot_users (user_id, welcomed, joined_at) VALUES (?, 0, ?)",
            (user_id, int(datetime.now().timestamp() * 1000)),
        )
        await db.commit()
        return {"user_id": user_id, "welcomed": 0}


async def mark_welcomed(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bot_users SET welcomed = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_session(user_id: int) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, state, context, updated_at FROM sessions WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return {"user_id": user_id, "state": "idle", "context": {}}
    try:
        context = json.loads(row[2]) if row[2] else {}
    except Exception:
        context = {}
    return {"user_id": user_id, "state": row[1], "context": context}


async def set_session(user_id: int, state: str, context: Optional[Dict] = None):
    ctx = json.dumps(context or {})
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO sessions (user_id, state, context, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 state = excluded.state,
                 context = excluded.context,
                 updated_at = excluded.updated_at""",
            (user_id, state, ctx, int(datetime.now().timestamp() * 1000)),
        )
        await db.commit()


async def clear_session(user_id: int):
    await set_session(user_id, "idle", {})


async def list_channels(owner_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, chat_id, title, username FROM channels WHERE owner_id = ? ORDER BY added_at ASC",
            (owner_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"id": r[0], "chat_id": r[1], "title": r[2], "username": r[3]} for r in rows]


async def get_channel_by_id(cid: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, chat_id, title, username, owner_id FROM channels WHERE id = ?", (cid,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "chat_id": row[1], "title": row[2], "username": row[3], "owner_id": row[4]}


async def upsert_channel(chat_id: int, title: str, username: Optional[str], owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO channels (chat_id, title, username, owner_id, added_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 title = excluded.title,
                 username = excluded.username,
                 owner_id = excluded.owner_id""",
            (chat_id, title, username, owner_id, int(datetime.now().timestamp() * 1000)),
        )
        await db.commit()


async def log_post(channel_db_id: int, message_id: Optional[int], post_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO posts_log (channel_id, message_id, post_type, sent_at) VALUES (?, ?, ?, ?)",
            (channel_db_id, message_id, post_type, int(datetime.now().timestamp() * 1000)),
        )
        await db.commit()


async def list_force_channels() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, chat_id, title, username, invite_link FROM force_channels ORDER BY added_at ASC"
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"id": r[0], "chat_id": r[1], "title": r[2], "username": r[3], "invite_link": r[4]}
        for r in rows
    ]


async def add_force_channel(chat_id: int, title: str, username: Optional[str], invite_link: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO force_channels (chat_id, title, username, invite_link, added_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 title = excluded.title,
                 username = excluded.username,
                 invite_link = excluded.invite_link""",
            (chat_id, title, username, invite_link, int(datetime.now().timestamp() * 1000)),
        )
        await db.commit()


async def delete_force_channel(cid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM force_channels WHERE id = ?", (cid,))
        await db.commit()


async def ensure_default_force_channel():
    try:
        channels = await list_force_channels()
        if any(c.get("username", "").lower() == "self_mr0" for c in channels):
            return True
        chat = await bot.get_chat(DEFAULT_FORCE_CHANNEL)
        invite = None
        if not chat.username:
            try:
                invite = await bot.export_chat_invite_link(chat.id)
            except Exception:
                pass
        await add_force_channel(
            chat.id,
            chat.title or "SELF_MR0",
            chat.username or "SELF_MR0",
            invite,
        )
        logger.info("Default force channel %s added", DEFAULT_FORCE_CHANNEL)
        return True
    except Exception as e:
        logger.error("Failed to ensure default force channel: %s", e)
        return False


async def check_force_subscription(user_id: int) -> Dict:
    channels = await list_force_channels()
    if not channels:
        return {"ok": True, "missing": []}
    missing = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["chat_id"], user_id)
            if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return {"ok": len(missing) == 0, "missing": missing, "all": channels}


# ──────────────────────────── کیبوردها ────────────────────────────
def main_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=color_label(0, "ارسال پست ✍️"), callback_data="menu:send"),
            InlineKeyboardButton(text=color_label(1, "ثبت کانال ☸️"), callback_data="menu:register"),
        ],
        [
            InlineKeyboardButton(text=color_label(2, "پشتیبانی 🛟"), callback_data="menu:support"),
            InlineKeyboardButton(text=color_label(0, "حمایت از سازنده 💎"), callback_data="menu:donate"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text=color_label(1, "تنظیمات ربات ⚙️"), callback_data="menu:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_button_row(callback_data: str = "nav:back_main"):
    return [InlineKeyboardButton(text=color_label(2, "بازگشت 🔙"), callback_data=callback_data)]


def back_only_keyboard(callback_data: str = "nav:back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[back_button_row(callback_data)])


def channel_list_keyboard(channels: List[Dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=color_label(i, c["title"]), callback_data=f"pickchan:{c['id']}")]
        for i, c in enumerate(channels)
    ]
    rows.append(back_button_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=color_label(0, "عکس 🖼"), callback_data="posttype:photo"),
                InlineKeyboardButton(text=color_label(1, "فیلم 🎬"), callback_data="posttype:video"),
            ],
            [
                InlineKeyboardButton(text=color_label(2, "فایل 📁"), callback_data="posttype:document"),
                InlineKeyboardButton(text=color_label(0, "متن 📝"), callback_data="posttype:text"),
            ],
            back_button_row(),
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=color_label(1, "بله، ارسال کن ✅"), callback_data="confirm:yes"),
                InlineKeyboardButton(text=color_label(0, "لغو ❌"), callback_data="confirm:no"),
            ]
        ]
    )


def donate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=color_label(1, "دونیت / حمایت 💎"), url=DONATE_URL)],
            back_button_row(),
        ]
    )


def settings_keyboard(mode: str) -> InlineKeyboardMarkup:
    toggle_text = "سوییچ به خصوصی 🔴" if mode == "public" else "سوییچ به عمومی 🟢"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=color_label(0 if mode == "public" else 1, toggle_text), callback_data="settings:togglemode")],
            [InlineKeyboardButton(text=color_label(2, "مدیریت جوین اجباری 📋"), callback_data="menu:forcelist")],
            back_button_row(),
        ]
    )


def force_list_keyboard(channels: List[Dict]) -> InlineKeyboardMarkup:
    rows = []
    for i, c in enumerate(channels):
        url = f"https://t.me/{c['username']}" if c.get("username") else c.get("invite_link")
        btn = InlineKeyboardButton(text=color_label(i, c["title"]), url=url) if url else InlineKeyboardButton(text=color_label(i, c["title"]), callback_data="noop")
        rows.append([btn, InlineKeyboardButton(text="🗑", callback_data=f"fcdel:{c['id']}")])
    rows.append([InlineKeyboardButton(text=color_label(1, "افزودن کانال ➕"), callback_data="fcadd")])
    rows.append(back_button_row("menu:settings"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def must_join_keyboard(channels: List[Dict]) -> InlineKeyboardMarkup:
    rows = []
    for i, c in enumerate(channels):
        url = f"https://t.me/{c['username']}" if c.get("username") else c.get("invite_link")
        if url:
            rows.append([InlineKeyboardButton(text=color_label(i, c["title"]), url=url)])
    rows.append([InlineKeyboardButton(text=color_label(2, "بررسی مجدد 🔄"), callback_data="fcheck")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────── منطق دسترسی ────────────────────────────
def is_admin(user_id: int) -> bool:
    return int(user_id) == ADMIN_ID


async def resolve_access(user_id: int) -> Dict:
    mode = await get_bot_mode()
    admin = is_admin(user_id)
    await ensure_user(user_id)
    if mode == "private" and not admin:
        return {"allowed": False, "is_admin": admin, "mode": mode}
    return {"allowed": True, "is_admin": admin, "mode": mode}


async def send_welcome_ad_if_needed(user_id: int):
    row = await ensure_user(user_id)
    if row["welcomed"] == 0:
        await bot.send_message(user_id, T["ad_once"])
        await mark_welcomed(user_id)


# ──────────────────────────── هندلرهای پیام ────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    access = await resolve_access(user_id)

    if not access["allowed"]:
        await message.answer(T["denied"])
        return

    await clear_session(user_id)
    await send_welcome_ad_if_needed(user_id)

    if access["mode"] == "public" and not access["is_admin"]:
        sub = await check_force_subscription(user_id)
        if not sub["ok"]:
            await message.answer(T["must_join"], reply_markup=must_join_keyboard(sub["missing"]))
            return

    await message.answer(T["welcome"], reply_markup=main_menu_keyboard(access["is_admin"]))


@dp.message(F.forward_from_chat | F.forward_origin)
async def handle_forward(message: Message):
    user_id = message.from_user.id
    session = await get_session(user_id)
    state = session["state"]

    if state == "awaiting_channel_forward":
        await handle_channel_forward(message)
    elif state == "awaiting_force_channel_forward":
        await handle_force_channel_forward(message)
    else:
        # ignore random forwards
        pass


async def handle_channel_forward(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    origin = None
    if message.forward_from_chat:
        origin = message.forward_from_chat
    elif message.forward_origin and hasattr(message.forward_origin, "chat"):
        origin = message.forward_origin.chat

    if not origin or origin.type not in ("channel", "supergroup"):
        await message.answer(
            "❗️ این پیام از یه کانال فوروارد نشده. لطفاً یه پست از کانالت رو مستقیم فوروارد کن.",
            reply_markup=back_only_keyboard(),
        )
        return

    target_chat_id = origin.id
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(target_chat_id, me.id)
        can_post = member.status == ChatMemberStatus.ADMINISTRATOR and getattr(member, "can_post_messages", False)
        if not can_post:
            await message.answer(
                "❗️ ربات توی این کانال دسترسی «ارسال پیام» نداره. لطفاً دسترسی رو بده و دوباره فوروارد کن.",
                reply_markup=back_only_keyboard(),
            )
            return
    except Exception:
        await message.answer(
            "❗️ ربات هنوز توی این کانال ادمین نیست یا بهش دسترسی داده نشده.",
            reply_markup=back_only_keyboard(),
        )
        return

    title = origin.title or "بدون نام"
    username = origin.username
    await upsert_channel(target_chat_id, title, username, user_id)
    await clear_session(user_id)

    access = await resolve_access(user_id)
    await message.answer(
        f"🏵 <b>اطلاعات کانال</b>\n\n• نام: {escape_html(title)}\n"
        f"• یوزرنیم: {'@' + escape_html(username) if username else 'ندارد'}\n\nکانال با موفقیت ثبت شد 🔸",
        reply_markup=main_menu_keyboard(access["is_admin"]),
    )


async def handle_force_channel_forward(message: Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    origin = None
    if message.forward_from_chat:
        origin = message.forward_from_chat
    elif message.forward_origin and hasattr(message.forward_origin, "chat"):
        origin = message.forward_origin.chat

    if not origin:
        await message.answer(
            "❗️ این پیام فوروارد نشده. لطفاً یه پست از کانال/گروه مورد نظر رو مستقیم فوروارد کن.",
            reply_markup=back_only_keyboard("menu:forcelist"),
        )
        return

    title = origin.title or "بدون نام"
    username = origin.username
    invite = None
    if not username:
        try:
            invite = await bot.export_chat_invite_link(origin.id)
        except Exception:
            pass

    await add_force_channel(origin.id, title, username, invite)
    await clear_session(user_id)
    await message.answer(
        f"🏵 کانال/گروه «{escape_html(title)}» به لیست جوین اجباری اضافه شد ✅",
        reply_markup=back_only_keyboard("menu:forcelist"),
    )


@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    access = await resolve_access(user_id)
    if not access["allowed"]:
        await message.answer(T["denied"])
        return

    if access["mode"] == "public" and not access["is_admin"]:
        sub = await check_force_subscription(user_id)
        if not sub["ok"]:
            await message.answer(T["must_join"], reply_markup=must_join_keyboard(sub["missing"]))
            return

    session = await get_session(user_id)
    state = session["state"]
    ctx = session["context"]

    if state == "awaiting_text_content":
        ctx["draft_text"] = message.text
        ctx["draft_entities"] = [e.model_dump() for e in (message.entities or [])]
        await go_to_preview(message, user_id, ctx)
    elif state == "awaiting_caption":
        text = message.text or ""
        if text.strip() != "بدون کپشن":
            ctx["draft_caption"] = text
            ctx["draft_caption_entities"] = [e.model_dump() for e in (message.entities or [])]
        await go_to_preview(message, user_id, ctx)
    else:
        await message.answer(T["welcome"], reply_markup=main_menu_keyboard(access["is_admin"]))


@dp.message(F.photo | F.video | F.document)
async def handle_media(message: Message):
    user_id = message.from_user.id
    session = await get_session(user_id)
    if session["state"] != "awaiting_media_content":
        return

    access = await resolve_access(user_id)
    if not access["allowed"]:
        return

    kind = session["context"].get("post_type")
    file_id = None
    if kind == "photo" and message.photo:
        file_id = message.photo[-1].file_id
    elif kind == "video" and message.video:
        file_id = message.video.file_id
    elif kind == "document" and message.document:
        file_id = message.document.file_id

    if not file_id:
        labels = {"photo": "عکس", "video": "فیلم", "document": "فایل"}
        await message.answer(
            f"❗️ این پیام یه {labels.get(kind, kind)} معتبر نیست. لطفاً دوباره بفرست.",
            reply_markup=back_only_keyboard(),
        )
        return

    ctx = {**session["context"], "file_id": file_id}
    await set_session(user_id, "awaiting_caption", ctx)
    await message.answer(T["ask_caption"], reply_markup=back_only_keyboard())


async def apply_emoji_placeholders(text: str) -> str:
    """جایگزینی ساده [id] با علامت موقت – تلگرام خودش custom_emoji رو هندل می‌کنه اگر entities درست باشه.
    در نسخه ساده فعلاً متن رو برمی‌گردونیم و اجازه می‌دیم کاربر از کلاینت تلگرام ایموجی بذاره.
    """
    return text


async def go_to_preview(message: Message, user_id: int, ctx: Dict):
    post_type = ctx.get("post_type")
    raw_text = ctx.get("draft_text") if post_type == "text" else ctx.get("draft_caption")

    final_text = raw_text
    ctx["final_text"] = final_text
    await set_session(user_id, "awaiting_confirmation", ctx)

    await message.answer(T["preview_header"])

    try:
        if post_type == "text":
            sent = await bot.send_message(message.chat.id, final_text or "", disable_web_page_preview=True)
        elif post_type == "photo":
            sent = await bot.send_photo(message.chat.id, ctx["file_id"], caption=final_text)
        elif post_type == "video":
            sent = await bot.send_video(message.chat.id, ctx["file_id"], caption=final_text)
        elif post_type == "document":
            sent = await bot.send_document(message.chat.id, ctx["file_id"], caption=final_text)
        else:
            await message.answer(T["generic_error"])
            return

        ctx["preview_chat_id"] = message.chat.id
        ctx["preview_message_id"] = sent.message_id
        await set_session(user_id, "awaiting_confirmation", ctx)

        await message.answer("برای تایید یا لغو یکی از دکمه‌های زیر رو بزن:", reply_markup=confirm_keyboard())
    except Exception as e:
        logger.error("Preview error: %s", e)
        await message.answer(T["bad_entities"], reply_markup=back_only_keyboard())
        if post_type == "text":
            await set_session(user_id, "awaiting_text_content", ctx)
        else:
            await set_session(user_id, "awaiting_caption", ctx)


# ──────────────────────────── کال‌بک‌ها ────────────────────────────
@dp.callback_query()
async def handle_callback(cb: CallbackQuery):
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id
    message_id = cb.message.message_id
    data = cb.data or ""

    access = await resolve_access(user_id)
    if not access["allowed"]:
        await cb.answer(T["denied"], show_alert=True)
        return

    await cb.answer()

    if data == "fcheck":
        sub = await check_force_subscription(user_id)
        if sub["ok"]:
            await cb.message.edit_text(
                T["joined_ok"] + "\n\n" + T["welcome"],
                reply_markup=main_menu_keyboard(access["is_admin"]),
            )
        else:
            await cb.answer(T["still_not_member"], show_alert=True)
        return

    if access["mode"] == "public" and not access["is_admin"]:
        sub = await check_force_subscription(user_id)
        if not sub["ok"]:
            await cb.message.edit_text(T["must_join"], reply_markup=must_join_keyboard(sub["missing"]))
            return

    action, _, param = data.partition(":")

    if action == "menu":
        await handle_menu(param, cb, access)
    elif action == "nav" and param == "back_main":
        await clear_session(user_id)
        await cb.message.edit_text(T["welcome"], reply_markup=main_menu_keyboard(access["is_admin"]))
    elif action == "pickchan":
        await handle_pick_channel(param, cb)
    elif action == "posttype":
        await handle_post_type(param, cb)
    elif action == "confirm":
        await handle_confirm(param, cb, access)
    elif action == "settings":
        await handle_settings(param, cb, access)
    elif action == "fcdel":
        await handle_force_delete(param, cb, access)
    elif action == "fcadd":
        if not access["is_admin"]:
            return
        await set_session(user_id, "awaiting_force_channel_forward", {})
        await cb.message.edit_text(T["register_force_instructions"], reply_markup=back_only_keyboard("menu:forcelist"))


async def handle_menu(param: str, cb: CallbackQuery, access: Dict):
    user_id = cb.from_user.id

    if param == "register":
        await set_session(user_id, "awaiting_channel_forward", {})
        await cb.message.edit_text(T["register_instructions"], reply_markup=back_only_keyboard())
    elif param == "send":
        channels = await list_channels(user_id)
        if not channels:
            await cb.message.edit_text(T["no_channels"], reply_markup=back_only_keyboard())
            return
        if len(channels) == 1:
            ctx = {"channel_db_id": channels[0]["id"], "channel_chat_id": channels[0]["chat_id"]}
            await set_session(user_id, "awaiting_post_type", ctx)
            await cb.message.edit_text(T["choose_post_type"], reply_markup=post_type_keyboard())
        else:
            await set_session(user_id, "awaiting_channel_selection", {})
            await cb.message.edit_text(T["choose_channel"], reply_markup=channel_list_keyboard(channels))
    elif param == "support":
        await cb.message.edit_text(T["support"], reply_markup=back_only_keyboard())
    elif param == "donate":
        await cb.message.edit_text(T["donate_intro"], reply_markup=donate_keyboard())
        await bot.send_message(cb.message.chat.id, T["donate_footer"])
    elif param == "settings":
        if not access["is_admin"]:
            return
        mode = await get_bot_mode()
        await cb.message.edit_text(
            f"⚙️ <b>تنظیمات ربات</b>\n\nحالت فعلی: {'🟢 عمومی' if mode == 'public' else '🔴 خصوصی'}\n\n"
            "در حالت عمومی همه کاربرها می‌تونن از ربات استفاده کنن.",
            reply_markup=settings_keyboard(mode),
        )
    elif param == "forcelist":
        if not access["is_admin"]:
            return
        channels = await list_force_channels()
        await cb.message.edit_text(
            f"📋 <b>کانال‌های جوین اجباری</b> ({len(channels)})\n\n"
            "کاربرها برای استفاده از ربات (در حالت عمومی) باید عضو همه این‌ها باشن.",
            reply_markup=force_list_keyboard(channels),
        )


async def handle_settings(param: str, cb: CallbackQuery, access: Dict):
    if not access["is_admin"]:
        return
    if param == "togglemode":
        current = await get_bot_mode()
        next_mode = "private" if current == "public" else "public"
        await set_setting("bot_mode", next_mode)
        await cb.message.edit_text(
            f"⚙️ <b>تنظیمات ربات</b>\n\nحالت فعلی: {'🟢 عمومی' if next_mode == 'public' else '🔴 خصوصی'}\n\n"
            "در حالت عمومی همه کاربرها می‌تونن از ربات استفاده کنن.",
            reply_markup=settings_keyboard(next_mode),
        )


async def handle_force_delete(param: str, cb: CallbackQuery, access: Dict):
    if not access["is_admin"]:
        return
    await delete_force_channel(int(param))
    channels = await list_force_channels()
    await cb.message.edit_text(
        T["force_channel_deleted"] + f"\n\n📋 <b>کانال‌های جوین اجباری</b> ({len(channels)})",
        reply_markup=force_list_keyboard(channels),
    )


async def handle_pick_channel(param: str, cb: CallbackQuery):
    user_id = cb.from_user.id
    channel = await get_channel_by_id(int(param))
    if not channel or channel["owner_id"] != user_id:
        await cb.message.edit_text(T["generic_error"], reply_markup=back_only_keyboard())
        return
    ctx = {"channel_db_id": channel["id"], "channel_chat_id": channel["chat_id"]}
    await set_session(user_id, "awaiting_post_type", ctx)
    await cb.message.edit_text(T["choose_post_type"], reply_markup=post_type_keyboard())


async def handle_post_type(param: str, cb: CallbackQuery):
    user_id = cb.from_user.id
    session = await get_session(user_id)
    ctx = {**session["context"], "post_type": param}

    if param == "text":
        await set_session(user_id, "awaiting_text_content", ctx)
        await cb.message.edit_text(T["ask_text"], reply_markup=back_only_keyboard())
    else:
        await set_session(user_id, "awaiting_media_content", ctx)
        labels = {"photo": "عکس", "video": "فیلم", "document": "فایل"}
        await cb.message.edit_text(
            f"لطفاً <b>{labels.get(param, param)}</b> مورد نظرت رو بفرست یا فوروارد کن.",
            reply_markup=back_only_keyboard(),
        )


async def handle_confirm(param: str, cb: CallbackQuery, access: Dict):
    user_id = cb.from_user.id
    session = await get_session(user_id)
    ctx = session["context"]

    if param == "no":
        await clear_session(user_id)
        await cb.message.edit_text(T["cancelled"], reply_markup=main_menu_keyboard(access["is_admin"]))
        return

    if param != "yes":
        return

    channel = await get_channel_by_id(ctx.get("channel_db_id"))
    if not channel or channel["owner_id"] != user_id:
        await cb.message.edit_text(
            "❗️ این کانال دیگه ثبت نیست. دوباره ثبتش کن.",
            reply_markup=main_menu_keyboard(access["is_admin"]),
        )
        await clear_session(user_id)
        return

    preview_chat = ctx.get("preview_chat_id")
    preview_msg = ctx.get("preview_message_id")
    if not preview_chat or not preview_msg:
        await cb.message.edit_text(T["generic_error"], reply_markup=main_menu_keyboard(access["is_admin"]))
        await clear_session(user_id)
        return

    try:
        # فوروارد پیش‌نمایش به کانال هدف
        sent = await bot.forward_message(
            chat_id=channel["chat_id"],
            from_chat_id=preview_chat,
            message_id=preview_msg,
        )
        await log_post(channel["id"], sent.message_id if sent else None, ctx.get("post_type"))
        await clear_session(user_id)
        await cb.message.edit_text(T["sent_ok"], reply_markup=main_menu_keyboard(access["is_admin"]))
    except Exception as e:
        logger.error("Forward error: %s", e)
        err = str(e).lower()
        if "403" in err or "forbidden" in err:
            text = "❗️ ربات از این کانال حذف شده یا دسترسی نداره. لطفاً دوباره ثبتش کن."
        elif "429" in err:
            text = "❗️ محدودیت ارسال تلگرام. کمی صبر کن و دوباره امتحان کن."
        else:
            text = T["generic_error"]
        await cb.message.edit_text(text, reply_markup=main_menu_keyboard(access["is_admin"]))


# ──────────────────────────── FastAPI / Webhook ────────────────────────────
@app.on_event("startup")
async def on_startup():
    await init_db()
    await ensure_default_force_channel()
    # ست کردن وبهوک (اختیاری – اگه Railway URL داری)
    webhook_url = os.getenv("WEBHOOK_URL")  # مثال: https://your-app.up.railway.app/webhook
    if webhook_url:
        await bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)
        logger.info("Webhook set to %s", webhook_url)
    else:
        logger.info("WEBHOOK_URL not set – running in polling mode is recommended for local test")


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = await request.json()
    from aiogram.types import Update
    update = Update(**data) if "update_id" in data else None
    if update:
        await dp.feed_update(bot, update)
    return Response(content="OK", status_code=200)


@app.get("/")
async def root():
    return {"status": "ok", "bot": "premium-emoji-bot", "admin": ADMIN_ID}


@app.get("/health")
async def health():
    return {"ok": True}


# ──────────────────────────── اجرای مستقیم (polling برای تست) ────────────────────────────
if __name__ == "__main__":
    import uvicorn
    # برای تست محلی می‌تونی polling هم اضافه کنی، ولی روی Railway از webhook استفاده کن
    uvicorn.run("bot:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
