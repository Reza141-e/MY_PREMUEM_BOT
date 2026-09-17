import uuid
import base64
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
import uvicorn
from fastapi import FastAPI
from config import *

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ذخیره موقت کانفیگ‌ها (برای لینک ساب ساده)
configs_store = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def generate_vless(uuid_str: str, remark: str = "Admin-Config") -> str:
    """ساخت لینک VLESS Reality"""
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

    # ذخیره برای ساب
    configs_store[new_uuid] = vless_link

    # ساخت لینک ساب ساده (base64)
    sub_content = base64.b64encode(vless_link.encode()).decode()
    sub_link = f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'your-app.up.railway.app')}/sub/{new_uuid}"

    text = (
        f"✅ کانفیگ جدید ساخته شد\n\n"
        f"**UUID:** `{new_uuid}`\n\n"
        f"**لینک کانفیگ:**\n`{vless_link}`\n\n"
        f"**لینک ساب:**\n`{sub_link}`\n\n"
        f"می‌تونی مستقیم کپی کنی."
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
    for uid, link in configs_store.items():
        text += f"`{uid[:8]}...` → ساخته شده\n"
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "راهنما:\n"
        "/create → ساخت کانفیگ VLESS Reality جدید\n"
        "/list → نمایش UUIDهای ساخته‌شده\n\n"
        "تنظیمات سرور از Environment Variables خوانده می‌شود."
    )


# ====================== FastAPI برای لینک ساب ======================
@app.get("/sub/{config_id}")
async def get_sub(config_id: str):
    if config_id in configs_store:
        content = configs_store[config_id]
        return base64.b64encode(content.encode()).decode()
    return "Config not found"


@app.get("/")
async def root():
    return {"status": "V2Ray Admin Bot is running"}


# ====================== اجرای همزمان بات و وب‌سرور ======================
async def main():
    # اجرای بات
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    import threading

    # اجرای FastAPI در ترد جدا
    def run_api():
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

    threading.Thread(target=run_api, daemon=True).start()
    asyncio.run(main())
