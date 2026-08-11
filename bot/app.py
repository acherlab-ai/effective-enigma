"""
Bringh Bot - Main Application
=============================

This is the main bot application that:
- Connects to Zalo API
- Processes incoming messages
- Handles text, images, and stickers
- Manages memory and statistics
- Provides admin functionality
"""

import asyncio
import os
import time
from collections import defaultdict
from typing import Optional, Dict, Any

import zalo_bot
from dotenv import load_dotenv

from bot.config import (
    ZALO_BOT_TOKEN,
    DATA_DIR,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_MAX_MESSAGES,
    BAN_MESSAGE,
    DEFAULT_MAINTENANCE_MESSAGE,
)
from bot.utils.security import (
    contains_jailbreak_attempt,
    security_monitor,
    load_banned,
    is_banned,
    ban_user,
    save_banned,
)
from bot.utils.memory import memory_manager, LegacyMemoryLoader
from bot.utils.stats import stats_manager, LegacyStatsLoader
from bot.handlers.text import text_handler
from bot.handlers.image import image_handler, sticker_handler
from bot.handlers.ai import ai_client


# ============================================================
# GLOBAL STATE
# ============================================================

# Rate limiting
_message_timestamps: Dict[str, List[float]] = defaultdict(list)

# Chat locks (for processing messages in order per chat)
chat_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# Admin state
_admin_state = {
    "maintenance": False,
    "maintenance_message": DEFAULT_MAINTENANCE_MESSAGE
}


# ============================================================
# RATE LIMIT
# ============================================================

def check_rate_limit(chat_id: str) -> bool:
    """
    Check if a message should be processed based on rate limiting.
    
    Args:
        chat_id: Chat ID to check
        
    Returns:
        True if message should be processed, False if rate limited
    """
    now = time.monotonic()
    timestamps = _message_timestamps[chat_id]
    
    # Remove old timestamps
    while timestamps and (now - timestamps[0]) > RATE_LIMIT_WINDOW:
        timestamps.pop(0)
    
    # Check if over limit
    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        return False
    
    # Add current timestamp
    timestamps.append(now)
    return True


# ============================================================
# ADMIN STATE MANAGEMENT
# ============================================================

def load_admin_state() -> Dict[str, Any]:
    """Load admin state from file."""
    import json
    from bot.config import ADMIN_STATE_FILE
    
    if ADMIN_STATE_FILE.exists():
        try:
            with open(ADMIN_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "maintenance": False,
        "maintenance_message": DEFAULT_MAINTENANCE_MESSAGE
    }


def save_admin_state(state: Dict[str, Any]):
    """Save admin state to file."""
    import json
    from bot.config import ADMIN_STATE_FILE
    
    try:
        tmp_path = ADMIN_STATE_FILE.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp_path.replace(ADMIN_STATE_FILE)
    except Exception as e:
        print(f"Error saving admin state: {e}")


# ============================================================
# MESSAGE SENDING
# ============================================================

async def safe_send(bot: Any, chat_id: str, text: str):
    """
    Safely send a message, splitting if too long.
    
    Args:
        bot: Zalo bot instance
        chat_id: Chat ID to send to
        text: Text to send
    """
    if not text:
        return
    
    # Zalo message length limit
    MAX_LENGTH = 4000
    
    if len(text) <= MAX_LENGTH:
        await bot.send_message(chat_id, text)
        return
    
    # Split long messages
    for i in range(0, len(text), MAX_LENGTH):
        chunk = text[i:i + MAX_LENGTH]
        await bot.send_message(chat_id, chunk)


# ============================================================
# MESSAGE HANDLING
# ============================================================

async def handle_update(bot: Any, update: Any):
    """
    Handle an incoming update from Zalo.
    
    Args:
        bot: Zalo bot instance
        update: Update object from Zalo API
    """
    try:
        if not update or not update.message:
            return
        
        message = update.message
        chat_id = str(message.chat.id)
        message_type = getattr(message, "message_type", "")
        
        print()
        print(f"📩 [{chat_id}] {message_type}")
        
        # ==================================================
        # CHECK BANNED USERS
        # ==================================================
        if is_banned(chat_id):
            print(f"🚫 [{chat_id}] Message ignored (banned)")
            return
        
        # ==================================================
        # CHECK RATE LIMIT
        # ==================================================
        if not check_rate_limit(chat_id):
            print(
                f"⏳ [{chat_id}] Rate limited: "
                f"{RATE_LIMIT_MAX_MESSAGES} messages/{RATE_LIMIT_WINDOW}s"
            )
            return
        
        # ==================================================
        # CHECK MAINTENANCE MODE
        # ==================================================
        admin_state = load_admin_state()
        if admin_state.get("maintenance", False):
            maintenance_message = admin_state.get(
                "maintenance_message",
                DEFAULT_MAINTENANCE_MESSAGE
            )
            await safe_send(bot, chat_id, maintenance_message)
            return
        
        # Process messages in order per chat
        async with chat_locks[chat_id]:
            # ==================================================
            # HANDLE DIFFERENT MESSAGE TYPES
            # ==================================================
            
            # Text messages
            if message_type == "CHAT_TEXT":
                await _handle_text_message(bot, chat_id, message)
            
            # Image messages
            elif message_type == "CHAT_PHOTO":
                await _handle_image_message(bot, chat_id, message)
            
            # Sticker messages (if supported)
            elif message_type == "CHAT_STICKER":
                await _handle_sticker_message(bot, chat_id, message)
            
            # Unknown message type
            else:
                print(f"⚠️ Unknown message type: {message_type}")
                
    except Exception as e:
        print()
        print(f"❌ HANDLE UPDATE ERROR: {repr(e)}")


async def _handle_text_message(bot: Any, chat_id: str, message: Any):
    """Handle a text message."""
    text = getattr(message, "text", None)
    if not text:
        return
    
    text = text.strip()
    if not text:
        return
    
    print(f"💬 [{chat_id}] {text}")
    
    # Check for jailbreak in text
    if contains_jailbreak_attempt(text):
        ban_user(chat_id, reason="prompt injection / jailbreak (text)")
        await safe_send(bot, chat_id, BAN_MESSAGE)
        return
    
    # Advanced security check
    if security_monitor.check_advanced(text, chat_id):
        ban_user(chat_id, reason="prompt injection / jailbreak (advanced)")
        await safe_send(bot, chat_id, BAN_MESSAGE)
        return
    
    # Process text
    print(f"🧠 [{chat_id}] Bringh đang suy nghĩ...")
    reply = await text_handler.handle(chat_id, text, bot)
    
    if reply:
        print(f"🤖 [{chat_id}] Bringh: {reply}")
        await safe_send(bot, chat_id, reply)


async def _handle_image_message(bot: Any, chat_id: str, message: Any):
    """Handle an image message."""
    photo_url = getattr(message, "photo_url", None)
    if not photo_url:
        print("⚠️ CHAT_PHOTO but no photo_url")
        return
    
    caption = getattr(message, "caption", "")
    
    print(f"🖼️ Ảnh: {photo_url}")
    if caption:
        print(f"📝 Caption: {caption}")
    
    # Check caption for jailbreak
    if caption and contains_jailbreak_attempt(caption):
        ban_user(chat_id, reason="prompt injection / jailbreak (caption)")
        await safe_send(bot, chat_id, BAN_MESSAGE)
        return
    
    print(f"🧠 [{chat_id}] Bringh đang xem ảnh...")
    reply = await image_handler.handle(chat_id, photo_url, caption, bot)
    
    if reply:
        print(f"🤖 [{chat_id}] Bringh: {reply}")
        await safe_send(bot, chat_id, reply)


async def _handle_sticker_message(bot: Any, chat_id: str, message: Any):
    """Handle a sticker message."""
    sticker_id = getattr(message, "sticker_id", "")
    sticker_category = getattr(message, "sticker_category", "")
    
    print(f"🎭 Sticker: {sticker_id} (category: {sticker_category})")
    
    reply = await sticker_handler.handle(
        chat_id,
        sticker_id,
        sticker_category
    )
    
    print(f"🤖 [{chat_id}] Bringh: {reply}")
    await safe_send(bot, chat_id, reply)


# ============================================================
# MAIN BOT FUNCTION
# ============================================================

async def main():
    """Main bot entry point."""
    # Load environment
    load_dotenv()
    
    # Initialize memory and stats
    await memory_manager.initialize()
    
    # Migrate legacy data (if exists)
    await LegacyMemoryLoader.migrate_to_sqlite(memory_manager)
    await LegacyStatsLoader.migrate_to_sqlite(stats_manager)
    
    # Create bot instance
    bot = zalo_bot.Bot(ZALO_BOT_TOKEN)
    
    async with bot:
        me = await bot.get_me()
        
        print()
        print("=" * 50)
        print("🐾 BRINGH ĐANG CHẠY")
        print("=" * 50)
        print(f"Bot: {me.account_name}")
        print(f"ID: {me.id}")
        print(f"AI: Online")
        print(f"VISION: Online")
        print(f"OCR: {os.getenv('OCR_PROVIDER', 'easyocr')}")
        print(f"DATABASE: SQLite ({DATABASE_FILE})")
        print("=" * 50)
        print()
        
        # Main loop
        while True:
            try:
                update = await bot.get_update(timeout=60)
                
                if not update:
                    continue
                
                # Process update in background task
                asyncio.create_task(
                    handle_update(bot, update)
                )
                
            except Exception as e:
                print()
                print(f"❌ BOT LOOP ERROR: {repr(e)}")
                await asyncio.sleep(3)


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bringh đã dừng.")
    finally:
        # Cleanup
        asyncio.run(ai_client.close())
