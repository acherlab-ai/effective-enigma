"""
Bringh Bot Configuration
========================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# ZALO BOT
# ============================================================
ZALO_BOT_TOKEN = os.getenv("ZALO_BOT_TOKEN")
if not ZALO_BOT_TOKEN:
    raise RuntimeError("Missing ZALO_BOT_TOKEN in .env")

# ============================================================
# AI PROVIDER (Mistral)
# ============================================================
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise RuntimeError("Missing MISTRAL_API_KEY in .env")

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = os.getenv("AI_MODEL", "mistral-small-latest")

# ============================================================
# OCR (Optional - for image text extraction)
# ============================================================
# Options: "tesseract", "easyocr", "google_vision"
OCR_PROVIDER = os.getenv("OCR_PROVIDER", "easyocr")
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")

# ============================================================
# DATA DIRECTORY
# ============================================================
DATA_DIR = Path(os.getenv("BRINGH_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database file (SQLite)
DATABASE_FILE = DATA_DIR / "bringh.db"

# Legacy JSON files (for backward compatibility)
CONTEXTS_FILE = DATA_DIR / "contexts_store.json"
FACTS_FILE = DATA_DIR / "facts_store.json"
STATS_FILE = DATA_DIR / "stats_store.json"
ADMIN_STATE_FILE = DATA_DIR / "admin_state.json"
BANNED_FILE = DATA_DIR / "banned_users.json"

# ============================================================
# RATE LIMIT
# ============================================================
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))  # seconds
RATE_LIMIT_MAX_MESSAGES = int(os.getenv("RATE_LIMIT_MAX_MESSAGES", 10))

# ============================================================
# MEMORY SETTINGS
# ============================================================
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", 40))
SUMMARY_TRIGGER = int(os.getenv("SUMMARY_TRIGGER", 60))
RECENT_AFTER_SUMMARY = int(os.getenv("RECENT_AFTER_SUMMARY", 20))

# ============================================================
# AI SETTINGS
# ============================================================
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1200))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))

# ============================================================
# DEFAULT MESSAGES
# ============================================================
DEFAULT_MAINTENANCE_MESSAGE = (
    "Bringh đang bảo trì xíu nha 🛠️ "
    "Lát quay lại nói chuyện tiếp nhé!"
)

BAN_MESSAGE = (
    "🚫 Tài khoản này đã bị chặn vĩnh viễn do phát hiện hành vi "
    "prompt injection / jailbreak (cố can thiệp vào hệ thống). "
    "Nếu bạn nghĩ đây là nhầm lẫn, vui lòng liên hệ admin để được "
    "xem xét mở lại."
)

# ============================================================
# ADMIN SETTINGS
# ============================================================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Hn0961718254@")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", 8080))
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())

# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = DATA_DIR / "bot.log"
