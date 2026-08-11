"""
Admin Database Module
=====================

Provides database access for the admin web interface.
Uses the same SQLite database as the bot for consistency.
"""

import json
import sqlite3
from datetime import date, datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from bot.config import (
    DATA_DIR,
    DATABASE_FILE,
    STATS_FILE,
    ADMIN_STATE_FILE,
    BANNED_FILE,
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():
    """Ensure database exists and has required tables."""
    # This is called by bot, but we'll ensure it here too
    from bot.utils.memory import init_database as init_memory_db
    from bot.utils.stats import init_database as init_stats_db
    init_memory_db()
    init_stats_db()


# ============================================================
# STATISTICS QUERIES
# ============================================================

def get_total_stats() -> Dict[str, Any]:
    """Get total statistics."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute("SELECT SUM(messages) FROM daily_stats")
        total_messages = cursor.fetchone()[0] or 0
        
        # Total tokens
        cursor.execute("SELECT SUM(tokens) FROM daily_stats")
        total_tokens = cursor.fetchone()[0] or 0
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM user_stats")
        total_users = cursor.fetchone()[0] or 0
        
        # Today's stats
        today = date.today().isoformat()
        cursor.execute("""
            SELECT messages, tokens, active_users
            FROM daily_stats
            WHERE date = ?
        """, (today,))
        today_row = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_messages": int(total_messages),
            "total_tokens": int(total_tokens),
            "total_users": int(total_users),
            "messages_today": today_row[0] if today_row else 0,
            "tokens_today": today_row[1] if today_row else 0,
            "active_users_today": today_row[2] if today_row else 0,
        }
    except Exception as e:
        print(f"Error getting total stats: {e}")
        return {
            "total_messages": 0,
            "total_tokens": 0,
            "total_users": 0,
            "messages_today": 0,
            "tokens_today": 0,
            "active_users_today": 0,
        }


def get_daily_stats(days: int = 14) -> List[Dict[str, Any]]:
    """Get daily statistics for the last N days."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date, messages, tokens
            FROM daily_stats
            ORDER BY date DESC
            LIMIT ?
        """, (days,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "date": row[0],
                "messages": row[1],
                "tokens": row[2]
            })
        
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting daily stats: {e}")
        return []


def get_top_users(limit: int = 30) -> List[Dict[str, Any]]:
    """Get top users by token usage."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id, total_messages, total_tokens, first_seen, last_seen
            FROM user_stats
            ORDER BY total_tokens DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "chat_id": row[0],
                "messages": row[1],
                "tokens": row[2],
                "first_seen": row[3],
                "last_seen": row[4]
            })
        
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting top users: {e}")
        return []


def get_user_stats(chat_id: str) -> Optional[Dict[str, Any]]:
    """Get statistics for a specific user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id, total_messages, total_tokens, first_seen, last_seen
            FROM user_stats
            WHERE chat_id = ?
        """, (chat_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "chat_id": row[0],
                "messages": row[1],
                "tokens": row[2],
                "first_seen": row[3],
                "last_seen": row[4]
            }
        return None
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return None


def search_users(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search users by chat_id or other criteria."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Search in chat_id
        cursor.execute("""
            SELECT chat_id, total_messages, total_tokens, first_seen, last_seen
            FROM user_stats
            WHERE chat_id LIKE ?
            ORDER BY total_tokens DESC
            LIMIT ?
        """, (f"%{query}%", limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "chat_id": row[0],
                "messages": row[1],
                "tokens": row[2],
                "first_seen": row[3],
                "last_seen": row[4]
            })
        
        conn.close()
        return results
    except Exception as e:
        print(f"Error searching users: {e}")
        return []


# ============================================================
# BANNED USERS
# ============================================================

def get_banned_users() -> List[Dict[str, Any]]:
    """Get list of banned users."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id, reason, banned_at
            FROM banned_users
            ORDER BY banned_at DESC
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "chat_id": row[0],
                "reason": row[1],
                "banned_at": row[2]
            })
        
        conn.close()
        return results
    except Exception:
        # Fallback to JSON file
        return _get_banned_from_json()


def _get_banned_from_json() -> List[Dict[str, Any]]:
    """Get banned users from legacy JSON file."""
    if not BANNED_FILE.exists():
        return []
    
    try:
        with open(BANNED_FILE, "r", encoding="utf-8") as f:
            banned = json.load(f)
        return [
            {"chat_id": cid, **info}
            for cid, info in banned.items()
        ]
    except Exception:
        return []


def ban_user(chat_id: str, reason: str = "Admin chặn tay") -> bool:
    """Ban a user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO banned_users (chat_id, reason, banned_at)
            VALUES (?, ?, ?)
        """, (chat_id, reason, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Also update JSON file for backward compatibility
        _update_banned_json()
        
        return True
    except Exception as e:
        print(f"Error banning user: {e}")
        return False


def unban_user(chat_id: str) -> bool:
    """Unban a user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM banned_users WHERE chat_id = ?", (chat_id,))
        
        conn.commit()
        conn.close()
        
        # Also update JSON file for backward compatibility
        _update_banned_json()
        
        return True
    except Exception as e:
        print(f"Error unbanning user: {e}")
        return False


def _update_banned_json():
    """Update JSON file from database."""
    try:
        banned_list = get_banned_users()
        banned_dict = {user["chat_id"]: {"reason": user["reason"], "banned_at": user["banned_at"]}
                      for user in banned_list}
        
        tmp_path = BANNED_FILE.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(banned_dict, f, ensure_ascii=False, indent=2)
        tmp_path.replace(BANNED_FILE)
    except Exception as e:
        print(f"Error updating banned JSON: {e}")


# ============================================================
# ADMIN STATE
# ============================================================

def get_admin_state() -> Dict[str, Any]:
    """Get admin state."""
    if ADMIN_STATE_FILE.exists():
        try:
            with open(ADMIN_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "maintenance": False,
        "maintenance_message": "Bringh đang bảo trì xíu nha 🛠️ Lát quay lại nói chuyện tiếp nhé!"
    }


def set_admin_state(state: Dict[str, Any]):
    """Set admin state."""
    try:
        tmp_path = ADMIN_STATE_FILE.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp_path.replace(ADMIN_STATE_FILE)
    except Exception as e:
        print(f"Error saving admin state: {e}")


# ============================================================
# MEMORY MANAGEMENT
# ============================================================

def get_long_term_memory(chat_id: str) -> str:
    """Get long-term memory for a user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT facts FROM long_term_memory
            WHERE chat_id = ?
        """, (chat_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else ""
    except Exception as e:
        print(f"Error getting long-term memory: {e}")
        return ""


def update_long_term_memory(chat_id: str, facts: str) -> bool:
    """Update long-term memory for a user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO long_term_memory (chat_id, facts)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET facts = ?
        """, (chat_id, facts, facts))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating long-term memory: {e}")
        return False


def get_short_term_memory(chat_id: str) -> List[Dict[str, Any]]:
    """Get short-term memory (context) for a user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT context FROM short_term_memory
            WHERE chat_id = ?
        """, (chat_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return []
    except Exception as e:
        print(f"Error getting short-term memory: {e}")
        return []


def reset_short_term_memory(chat_id: str) -> bool:
    """Reset short-term memory for a user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE short_term_memory
            SET context = '[]'
            WHERE chat_id = ?
        """, (chat_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error resetting short-term memory: {e}")
        return False


def forget_user(chat_id: str) -> bool:
    """Forget all memory for a user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Delete short-term memory
        cursor.execute("DELETE FROM short_term_memory WHERE chat_id = ?", (chat_id,))
        
        # Delete long-term memory
        cursor.execute("DELETE FROM long_term_memory WHERE chat_id = ?", (chat_id,))
        
        # Delete user stats
        cursor.execute("DELETE FROM user_stats WHERE chat_id = ?", (chat_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error forgetting user: {e}")
        return False


# ============================================================
# LOGGING
# ============================================================

def get_recent_activity(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent message activity."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id, message_type, tokens, timestamp
            FROM message_log
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "chat_id": row[0],
                "message_type": row[1],
                "tokens": row[2],
                "timestamp": row[3]
            })
        
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return []


def get_jailbreak_attempts(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent jailbreak attempts."""
    # This would need to be tracked separately
    # For now, return empty list
    return []


# ============================================================
# SYSTEM INFO
# ============================================================

def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    return {
        "database_file": str(DATABASE_FILE),
        "data_dir": str(DATA_DIR),
        "database_size": _get_database_size(),
    }


def _get_database_size() -> int:
    """Get database file size in bytes."""
    try:
        return DATABASE_FILE.stat().st_size
    except Exception:
        return 0


# Initialize database on module load
init_database()
