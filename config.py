import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# تنظیمات سرور V2Ray (این‌ها را در Railway ست کن)
SERVER_HOST = os.getenv("SERVER_HOST", "your.domain.com")
SERVER_PORT = int(os.getenv("SERVER_PORT", "443"))
SNI = os.getenv("SNI", "www.cloudflare.com")
PBK = os.getenv("PBK", "")          # Public Key Reality
SID = os.getenv("SID", "")          # Short ID
FLOW = os.getenv("FLOW", "xtls-rprx-vision")
FP = os.getenv("FP", "chrome")
SPX = os.getenv("SPX", "/")         # SpiderX
