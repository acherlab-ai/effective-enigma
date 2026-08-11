"""
Memory Module - Short-term and Long-term Memory Management
=========================================================

This module handles:
- Short-term memory (conversation context)
- Long-term memory (user facts and preferences)
- Context compression and summarization
"""

import json
import asyncio
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from bot.config import (
    DATA_DIR,
    DATABASE_FILE,
    CONTEXTS_FILE,
    FACTS_FILE,
    MAX_MESSAGES,
    SUMMARY_TRIGGER,
    RECENT_AFTER_SUMMARY,
)


# ============================================================
# DATABASE SETUP
# ============================================================

def init_database():
    """Initialize SQLite database for memory storage."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Short-term memory (conversation context)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS short_term_memory (
            chat_id TEXT PRIMARY KEY,
            context TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Long-term memory (user facts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memory (
            chat_id TEXT PRIMARY KEY,
            facts TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Memory statistics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            memory_type TEXT,
            action TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


# ============================================================
# SHORT-TERM MEMORY (Conversation Context)
# ============================================================

class ShortTermMemory:
    """
    Manages short-term memory (conversation context) for each chat.
    Uses a combination of in-memory storage and SQLite for persistence.
    """
    
    def __init__(self):
        self._contexts: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._loaded = False
    
    async def load_from_db(self):
        """Load all contexts from SQLite database."""
        if self._loaded:
            return
        
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id, context FROM short_term_memory")
            
            for chat_id, context_json in cursor.fetchall():
                try:
                    self._contexts[chat_id] = json.loads(context_json)
                except json.JSONDecodeError:
                    self._contexts[chat_id] = []
            
            conn.close()
            self._loaded = True
        except Exception as e:
            print(f"Error loading short-term memory: {e}")
    
    async def save_to_db(self, chat_id: str):
        """Save context for a specific chat to database."""
        if not self._loaded:
            await self.load_from_db()
        
        context_json = json.dumps(self._contexts.get(chat_id, []), ensure_ascii=False)
        
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO short_term_memory (chat_id, context)
                VALUES (?, ?)
            """, (chat_id, context_json))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving short-term memory: {e}")
    
    async def get_context(self, chat_id: str) -> List[Dict]:
        """Get conversation context for a chat."""
        if not self._loaded:
            await self.load_from_db()
        return self._contexts.get(chat_id, [])
    
    async def add_message(self, chat_id: str, role: str, content: Any):
        """Add a message to the conversation context."""
        if not self._loaded:
            await self.load_from_db()
        
        message = {"role": role, "content": content}
        self._contexts[chat_id].append(message)
        
        # Trim context if too long
        if len(self._contexts[chat_id]) > MAX_MESSAGES:
            self._contexts[chat_id] = self._contexts[chat_id][-MAX_MESSAGES:]
        
        await self.save_to_db(chat_id)
    
    async def reset_context(self, chat_id: str):
        """Reset (clear) conversation context for a chat."""
        self._contexts[chat_id] = []
        await self.save_to_db(chat_id)
    
    async def compress_context(self, chat_id: str, summarizer_func) -> List[Dict]:
        """
        Compress context by summarizing old messages.
        
        Args:
            chat_id: Chat ID to compress
            summarizer_func: Function to generate summary (async)
            
        Returns:
            Compressed context
        """
        if not self._loaded:
            await self.load_from_db()
        
        history = self._contexts.get(chat_id, [])
        
        if len(history) < SUMMARY_TRIGGER:
            return history
        
        old_messages = history[:-RECENT_AFTER_SUMMARY]
        recent_messages = history[-RECENT_AFTER_SUMMARY:]
        
        # Generate summary
        summary = await summarizer_func(old_messages)
        
        # New context with summary
        new_context = [
            {
                "role": "system",
                "content": f"MEMORY CŨ:\n{summary}"
            }
        ] + recent_messages
        
        self._contexts[chat_id] = new_context
        await self.save_to_db(chat_id)
        
        return new_context
    
    async def get_all_contexts(self) -> Dict[str, List[Dict]]:
        """Get all contexts (for backup/export)."""
        if not self._loaded:
            await self.load_from_db()
        return dict(self._contexts)


# ============================================================
# LONG-TERM MEMORY (User Facts)
# ============================================================

class LongTermMemory:
    """
    Manages long-term memory (facts about users) for each chat.
    """
    
    def __init__(self):
        self._facts: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._loaded = False
    
    async def load_from_db(self):
        """Load all facts from SQLite database."""
        if self._loaded:
            return
        
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id, facts FROM long_term_memory")
            
            for chat_id, facts in cursor.fetchall():
                self._facts[chat_id] = facts
            
            conn.close()
            self._loaded = True
        except Exception as e:
            print(f"Error loading long-term memory: {e}")
    
    async def save_to_db(self, chat_id: str):
        """Save facts for a specific chat to database."""
        if not self._loaded:
            await self.load_from_db()
        
        facts = self._facts.get(chat_id, "")
        
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO long_term_memory (chat_id, facts)
                VALUES (?, ?)
            """, (chat_id, facts))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving long-term memory: {e}")
    
    async def get_facts(self, chat_id: str) -> str:
        """Get long-term facts for a chat."""
        if not self._loaded:
            await self.load_from_db()
        return self._facts.get(chat_id, "")
    
    async def update_facts(self, chat_id: str, new_facts: str):
        """Update long-term facts for a chat."""
        if not self._loaded:
            await self.load_from_db()
        
        self._facts[chat_id] = new_facts.strip()
        await self.save_to_db(chat_id)
    
    async def clear_facts(self, chat_id: str):
        """Clear long-term facts for a chat."""
        self._facts[chat_id] = ""
        await self.save_to_db(chat_id)
    
    async def get_all_facts(self) -> Dict[str, str]:
        """Get all facts (for backup/export)."""
        if not self._loaded:
            await self.load_from_db()
        return dict(self._facts)


# ============================================================
# MEMORY MANAGER (Combined)
# ============================================================

class MemoryManager:
    """
    Combined memory manager for both short-term and long-term memory.
    """
    
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
    
    async def initialize(self):
        """Initialize both memory systems."""
        init_database()
        await self.short_term.load_from_db()
        await self.long_term.load_from_db()
    
    async def build_messages(self, chat_id: str, system_prompt: str) -> List[Dict]:
        """
        Build messages for AI API call, including system prompt and memory.
        
        Args:
            chat_id: Chat ID
            system_prompt: Base system prompt
            
        Returns:
            List of messages for AI
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add long-term facts
        facts = await self.long_term.get_facts(chat_id)
        if facts:
            messages.append({
                "role": "system",
                "content": f"TRÍ NHỚ VỀ NGƯỜI DÙNG (những điều bạn đã biết từ trước, hãy dùng tự nhiên, đừng liệt kê ra):\n{facts}"
            })
        
        # Add short-term context
        context = await self.short_term.get_context(chat_id)
        messages.extend(context)
        
        return messages
    
    async def add_user_message(self, chat_id: str, content: Any):
        """Add user message to short-term memory."""
        await self.short_term.add_message(chat_id, "user", content)
    
    async def add_assistant_message(self, chat_id: str, content: str):
        """Add assistant message to short-term memory."""
        await self.short_term.add_message(chat_id, "assistant", content)
    
    async def reset_short_term(self, chat_id: str):
        """Reset short-term memory for a chat."""
        await self.short_term.reset_context(chat_id)
    
    async def forget_all(self, chat_id: str):
        """Forget all memory (short-term and long-term) for a chat."""
        await self.reset_short_term(chat_id)
        await self.long_term.clear_facts(chat_id)
    
    async def update_long_term(self, chat_id: str, extractor_func):
        """
        Update long-term memory using an extraction function.
        
        Args:
            chat_id: Chat ID
            extractor_func: Function to extract facts from messages
        """
        context = await self.short_term.get_context(chat_id)
        if not context:
            return
        
        current_facts = await self.long_term.get_facts(chat_id)
        new_facts = await extractor_func(context, current_facts)
        
        if new_facts and new_facts.strip():
            await self.long_term.update_facts(chat_id, new_facts)


# ============================================================
# LEGACY JSON COMPATIBILITY
# ============================================================

class LegacyMemoryLoader:
    """Load memory from legacy JSON files for backward compatibility."""
    
    @staticmethod
    def load_contexts() -> Dict[str, List[Dict]]:
        """Load contexts from legacy JSON file."""
        if not CONTEXTS_FILE.exists():
            return {}
        
        try:
            with open(CONTEXTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    @staticmethod
    def load_facts() -> Dict[str, str]:
        """Load facts from legacy JSON file."""
        if not FACTS_FILE.exists():
            return {}
        
        try:
            with open(FACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    @staticmethod
    async def migrate_to_sqlite(memory_manager: MemoryManager):
        """Migrate legacy JSON data to SQLite."""
        contexts = LegacyMemoryLoader.load_contexts()
        facts = LegacyMemoryLoader.load_facts()
        
        for chat_id, context_list in contexts.items():
            context_json = json.dumps(context_list, ensure_ascii=False)
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO short_term_memory (chat_id, context)
                    VALUES (?, ?)
                """, (chat_id, context_json))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error migrating context for {chat_id}: {e}")
        
        for chat_id, fact_text in facts.items():
            try:
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO long_term_memory (chat_id, facts)
                    VALUES (?, ?)
                """, (chat_id, fact_text))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error migrating facts for {chat_id}: {e}")
        
        print("Legacy data migration complete!")


# Global memory manager instance
memory_manager = MemoryManager()
