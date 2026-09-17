import os
import uuid
import base64
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
import uvicorn
from fastapi import FastAPI
from config import *

# لاگ‌ها را فعال می‌کنیم تا ببینی چی می‌شه
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

configs_store = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def generate_vless(uuid_str: str, remark: str = "Admin-Config") -> str:
    link = (
        f"vless://{uuid_str}@{SERVER_HOST}:{SERVER_PORT}"
        f"?encryption=none"
        f"&flow={FLOW}"
        f"&security=reality"
        f"&sni={SNI}"
        f"&fp={FP}"
        f"&pbk={PBK}"
        f"&sid={SID}"
        f"&spx={SPX}"
        f"&type=tcp"
        f"#{remark}"
    )
    return link


@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ شما ادمین نیستید.")
        return

    text = (
        "سلام ادمین 👋\n\n"
        "دستورات موجود:\n"
        "/create  ← ساخت کانفیگ جدید\n"
        "/list    ← لیست کانفیگ‌های ساخته‌شده\n"
        "/help    ← راهنما"
    )
    await message.answer(text)


@dp.message(Command("create"))
async def cmd_create(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ دسترسی ندارید.")
        return

    new_uuid = str(uuid.uuid4())
    remark = f"Admin-{new_uuid[:8]}"
    vless_link = generate_vless(new_uuid, remark)

    configs_store[new_uuid] = vless_link

    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RAILWAY_STATIC_URL") or "your-app.up.railway.app"
    sub_link = f"https://{domain}/sub/{new_uuid}"

    text = (
        f"✅ کانفیگ جدید ساخته شد\n\n"
        f"**UUID:** `{new_uuid}`\n\n"
        f"**لینک کانفیگ:**\n`{vless_link}`\n\n"
        f"**لینک ساب:**\n`{sub_link}`"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not configs_store:
        await message.answer("هنوز کانفیگی ساخته نشده.")
        return

    text = "📋 لیست کانفیگ‌ها:\n\n"
    for uid in configs_store:
        text += f"`{uid[:8]}...`\n"
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "راهنما:\n"
        "/create → ساخت کانفیگ VLESS Reality جدید\n"
        "/list → نمایش UUIDهای ساخته‌شده"
    )


@app.get("/sub/{config_id}")
async def get_sub(config_id: str):
    if config_id in configs_store:
        content = configs_store[config_id]
        return base64.b64encode(content.encode()).decode()
    return "Config not found"


@app.get("/")
async def root():
    return {"status": "V2Ray Admin Bot is running", "bot": "active"}


async def start_bot():
    logger.info("Starting Telegram bot polling...")
    await dp.start_polling(bot)


async def main():
    # بات را در پس‌زمینه اجرا می‌کنیم
    bot_task = asyncio.create_task(start_bot())

    # وب‌سرور را اجرا می‌کنیم
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

    await bot_task


if __name__ == "__main__":
    asyncio.run(main())
