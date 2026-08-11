"""
Statistics Module - Usage Tracking and Analytics
===============================================

This module handles:
- Message and token usage tracking
- User statistics
- Daily/weekly/monthly analytics
- Database-backed storage with SQLite
"""

import json
import asyncio
import sqlite3
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from bot.config import (
    DATA_DIR,
    DATABASE_FILE,
    STATS_FILE,
)


# ============================================================
# DATABASE SETUP
# ============================================================

def init_database():
    """Initialize SQLite database for statistics."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Daily statistics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            messages INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            new_users INTEGER DEFAULT 0
        )
    """)
    
    # User statistics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            chat_id TEXT PRIMARY KEY,
            total_messages INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            first_seen TEXT,
            last_seen TEXT,
            last_active TEXT
        )
    """)
    
    # Message log (for detailed analytics)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            message_type TEXT,
            tokens INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # System token usage (for context compression, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tokens INTEGER DEFAULT 0,
            purpose TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


# ============================================================
# STATISTICS MANAGER
# ============================================================

class StatisticsManager:
    """
    Manages all statistics and analytics for the bot.
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
    
    async def record_user_message(
        self,
        chat_id: str,
        tokens_used: int = 0,
        message_type: str = "text"
    ):
        """
        Record a user message and token usage.
        
        Args:
            chat_id: User/Group ID
            tokens_used: Number of tokens used for this message
            message_type: Type of message (text, image, sticker)
        """
        today = date.today().isoformat()
        now = datetime.now().isoformat()
        
        async with self._lock:
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                
                # Update daily stats
                cursor.execute("""
                    INSERT INTO daily_stats (date, messages, tokens)
                    VALUES (?, 1, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        messages = messages + 1,
                        tokens = tokens + ?,
                        active_users = active_users + 1
                """, (today, tokens_used, tokens_used))
                
                # Update or insert user stats
                cursor.execute("""
                    INSERT INTO user_stats (chat_id, total_messages, total_tokens, first_seen, last_seen, last_active)
                    VALUES (?, 1, ?, ?, ?, ?)
                    ON CONFLICT(chat_id) DO UPDATE SET
                        total_messages = total_messages + 1,
                        total_tokens = total_tokens + ?,
                        last_seen = ?,
                        last_active = ?
                """, (
                    chat_id,
                    tokens_used,
                    now,
                    now,
                    now,
                    tokens_used,
                    now,
                    now
                ))
                
                # Log message
                cursor.execute("""
                    INSERT INTO message_log (chat_id, message_type, tokens)
                    VALUES (?, ?, ?)
                """, (chat_id, message_type, tokens_used))
                
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error recording user message: {e}")
    
    async def record_system_tokens(
        self,
        tokens_used: int,
        purpose: str = "context_compression"
    ):
        """
        Record system token usage (for internal operations).
        
        Args:
            tokens_used: Number of tokens used
            purpose: Purpose of token usage
        """
        if not tokens_used:
            return
        
        async with self._lock:
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO system_tokens (tokens, purpose)
                    VALUES (?, ?)
                """, (tokens_used, purpose))
                
                # Update daily system tokens
                today = date.today().isoformat()
                cursor.execute("""
                    UPDATE daily_stats
                    SET tokens = tokens + ?
                    WHERE date = ?
                """, (tokens_used, today))
                
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error recording system tokens: {e}")
    
    async def get_total_stats(self) -> Dict[str, Any]:
        """Get total statistics across all time."""
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
            
            # System tokens
            cursor.execute("SELECT SUM(tokens) FROM system_tokens")
            system_tokens = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                "total_messages": int(total_messages),
                "total_tokens": int(total_tokens),
                "total_users": int(total_users),
                "system_tokens": int(system_tokens),
            }
        except Exception as e:
            print(f"Error getting total stats: {e}")
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "total_users": 0,
                "system_tokens": 0,
            }
    
    async def get_daily_stats(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        Get daily statistics for the last N days.
        
        Args:
            days: Number of days to fetch
            
        Returns:
            List of daily stats, most recent first
        """
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
    
    async def get_top_users(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Get top users by token usage.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of top users
        """
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
    
    async def get_user_stats(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific user.
        
        Args:
            chat_id: User/Group ID
            
        Returns:
            User statistics or None if not found
        """
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
    
    async def get_today_stats(self) -> Dict[str, Any]:
        """Get statistics for today."""
        today = date.today().isoformat()
        
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT messages, tokens, active_users
                FROM daily_stats
                WHERE date = ?
            """, (today,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "messages": row[0],
                    "tokens": row[1],
                    "active_users": row[2]
                }
            return {"messages": 0, "tokens": 0, "active_users": 0}
        except Exception as e:
            print(f"Error getting today stats: {e}")
            return {"messages": 0, "tokens": 0, "active_users": 0}
    
    async def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent message activity.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages
        """
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
    
    async def export_stats(self) -> Dict[str, Any]:
        """
        Export all statistics for backup.
        
        Returns:
            Complete statistics data
        """
        return {
            "total": await self.get_total_stats(),
            "daily": await self.get_daily_stats(30),
            "top_users": await self.get_top_users(100),
            "today": await self.get_today_stats(),
        }


# ============================================================
# LEGACY JSON COMPATIBILITY
# ============================================================

class LegacyStatsLoader:
    """Load statistics from legacy JSON file for backward compatibility."""
    
    @staticmethod
    def load_stats() -> Dict[str, Any]:
        """Load stats from legacy JSON file."""
        if not STATS_FILE.exists():
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "messages_by_day": {},
                "tokens_by_day": {},
                "users": {}
            }
        
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "messages_by_day": {},
                "tokens_by_day": {},
                "users": {}
            }
    
    @staticmethod
    async def migrate_to_sqlite(stats_manager: StatisticsManager):
        """Migrate legacy JSON stats to SQLite."""
        legacy_stats = LegacyStatsLoader.load_stats()
        
        # Migrate daily stats
        for date_str, messages in legacy_stats.get("messages_by_day", {}).items():
            tokens = legacy_stats.get("tokens_by_day", {}).get(date_str, 0)
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO daily_stats (date, messages, tokens)
                    VALUES (?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        messages = messages + ?,
                        tokens = tokens + ?
                """, (date_str, messages, tokens, messages, tokens))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error migrating daily stats for {date_str}: {e}")
        
        # Migrate user stats
        for chat_id, user_data in legacy_stats.get("users", {}).items():
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_stats (chat_id, total_messages, total_tokens, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id) DO UPDATE SET
                        total_messages = total_messages + ?,
                        total_tokens = total_tokens + ?
                """, (
                    chat_id,
                    user_data.get("messages", 0),
                    user_data.get("tokens", 0),
                    user_data.get("first_seen", ""),
                    user_data.get("last_seen", ""),
                    user_data.get("messages", 0),
                    user_data.get("tokens", 0)
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error migrating user stats for {chat_id}: {e}")
        
        print("Legacy stats migration complete!")


# Global statistics manager instance
stats_manager = StatisticsManager()


# Initialize database on module load
init_database()
