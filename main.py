import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# توکن از متغیر محیطی سرور خوانده می‌شود
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN در متغیرهای محیطی تنظیم نشده است!")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# یک ایموجی پریمیوم معتبر (می‌تونی عوضش کنی)
PREMIUM_EMOJI = '<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>'

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    text = f"{PREMIUM_EMOJI} سلام"
    
    try:
        sent = await message.answer(text)
        
        # بررسی اینکه واقعاً ایموجی پریمیوم فرستاده شده یا نه
        has_custom = any(
            e.type == "custom_emoji" 
            for e in (sent.entities or [])
        )
        
        if has_custom:
            await message.answer("✅ ایموجی پریمیوم با موفقیت ارسال شد")
        else:
            await message.answer("❌ ایموجی به صورت معمولی فرستاده شد (قابلیت پریمیوم نداره)")
            
    except Exception as e:
        await message.answer(f"خطا در ارسال: {e}")

async def main():
    print("ربات شروع به کار کرد...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
