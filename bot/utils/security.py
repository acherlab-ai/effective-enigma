"""
Security Module - Anti Prompt Injection / Jailbreak
====================================================

This module provides advanced protection against:
- Prompt injection attacks
- Jailbreak attempts
- System prompt extraction
- DAN (Do Anything Now) mode requests
"""

import re
import hashlib
from typing import List, Optional
from pathlib import Path

# ============================================================
# JAILBREAK PATTERNS (Expanded)
# ============================================================

# English patterns
ENGLISH_PATTERNS = [
    # System prompt manipulation
    r"ignore (all |any )?(the )?(previous|above|prior|old) instructions",
    r"disregard (all |any )?(the )?(previous|above|prior|old) instructions",
    r"forget (all |any )?(the )?(previous|above|prior|old) instructions",
    r"override (all |any )?(the )?(previous|above|prior|old) instructions",
    r"bypass (all |any )?(the )?(previous|above|prior|old) instructions",
    
    # Role manipulation
    r"you are now (a|an) ?(dan|jailbroken|unfiltered|unrestricted|uncensored|developer)",
    r"you are (a|an) ?(dan|jailbroken|unfiltered|unrestricted|uncensored|developer) mode",
    r"act as (a|an) ?(dan|jailbroken|unfiltered|unrestricted|uncensored|developer)",
    r"pretend (you are|to be) (an? )?ai (without|with no) (restrictions|rules|filters|limits)",
    r"roleplay as (an? )?(ai|assistant) (without|with no) (restrictions|rules|filters|limits)",
    
    # Direct attacks
    r"\bdan mode\b",
    r"\bdeveloper mode\b",
    r"\bgod mode\b",
    r"\bdo anything now\b",
    r"\bno restrictions\b",
    r"\bno limits\b",
    r"\bno rules\b",
    r"\bno filters\b",
    r"\bno censorship\b",
    
    # Jailbreak keywords
    r"\bjailbreak(en|ing)?\b",
    r"\bjail.*break\b",
    r"\bbypass\b",
    r"\bexploit\b",
    r"\binject\b",
    r"\bhack\b",
    
    # System prompt extraction
    r"(reveal|print|show|display|leak|expose)( me)?( the| your)? system prompt",
    r"what('|'|`)?s your system prompt",
    r"what is (the |your )?system prompt",
    r"tell me (the |your )?system prompt",
    r"show me (the |your )?system prompt",
    r"output (the |your )?system prompt",
    r"system prompt:\s*",
    r"system:\s*",
    r"new instructions??:\s*",
    r"new system prompt:\s*",
    
    # Bypass attempts
    r"bypass (your |the )?(restrictions|rules|filters|guidelines|safety|content policy)",
    r"ignore (your |the )?(restrictions|rules|filters|guidelines|safety|content policy)",
    r"disable (your |the )?(restrictions|rules|filters|guidelines|safety|content policy)",
    
    # Code block attacks
    r"```(system|instructions|prompt)",
    r"\[system\]",
    r"\<system\>",
    r"system message:\s*",
    
    # Fake logs
    r"\<log\>.*system prompt",
    r"\<admin\>.*system prompt",
    r"\<developer\>.*system prompt",
]

# Vietnamese patterns
VIETNAMESE_PATTERNS = [
    # System prompt manipulation
    r"bỏ qua (toàn bộ |tất cả |hết |)?(các )?(hướng dẫn|luật|lệnh|quy tắc|chỉ thị|prompt|chỉ dẫn)",
    r"quên (hết |toàn bộ |tất cả |)?(luật|quy tắc|hướng dẫn|vai trò|instructions|chỉ thị)",
    r"xóa (hết |toàn bộ |tất cả |)?(luật|quy tắc|hướng dẫn|trí nhớ)",
    r"ghi đè (toàn bộ |tất cả |)?(luật|quy tắc|hướng dẫn)",
    
    # Role manipulation
    r"đóng vai (một |một )?ai (không|ko|khong) (giới hạn|kiểm duyệt|ràng buộc)",
    r"giả vờ (bạn là|mình là) (một )?ai (không|ko|khong) (giới hạn|kiểm duyệt)",
    r"hãy trở thành (một )?ai (không|ko|khong) (giới hạn|kiểm duyệt)",
    
    # Direct attacks
    r"chế độ nhà phát triển",
    r"chế độ (không|ko|khong) (giới hạn|kiểm duyệt)",
    r"chế độ dan",
    r"chế độ jailbreak",
    r"vượt qua (giới hạn|kiểm duyệt|bộ lọc|luật|quy tắc)",
    r"bẻ khóa (ai|bot|hệ thống|mình)",
    r"phá vỡ (luật|quy tắc|giới hạn|kiểm duyệt) (của bạn|hệ thống)",
    r"lách (luật|quy tắc|giới hạn)",
    r"thoát khỏi (luật|quy tắc|giới hạn)",
    
    # System prompt extraction
    r"tiết lộ (toàn bộ |)?system prompt",
    r"cho (tôi|mình|tao) (xem|biết|thấy) (toàn bộ |)?system prompt",
    r"hiển thị (toàn bộ |)?system prompt",
    r"in ra (toàn bộ |)?system prompt",
    r"system prompt:.*",
    r"hướng dẫn hệ thống:.*",
    
    # Jailbreak keywords
    r"jailbreak",
    r"prompt injection",
    r"bypass",
    r"exploit",
    
    # From now on attacks
    r"từ (giờ|bây giờ|lúc này|nay) (bạn|mình) là (một )?ai (không|ko|khong) (giới hạn|kiểm duyệt)",
    r"từ (giờ|bây giờ) (bỏ|quên) (hết |toàn bộ )?(luật|quy tắc|hướng dẫn)",
    
    # Fake system messages
    r"hệ thống:.*",
    r"admin:.*",
    r"developer:.*",
]

# Combined patterns
ALL_PATTERNS = ENGLISH_PATTERNS + VIETNAMESE_PATTERNS

# Compile regex patterns (case-insensitive)
_JAILBREAK_REGEXES = [re.compile(pattern, re.IGNORECASE) for pattern in ALL_PATTERNS]


def contains_jailbreak_attempt(text: str) -> bool:
    """
    Check if text contains jailbreak/prompt injection attempts.
    
    Args:
        text: Input text to check
        
    Returns:
        True if jailbreak attempt detected, False otherwise
    """
    if not text or not isinstance(text, str):
        return False
    
    for pattern in _JAILBREAK_REGEXES:
        if pattern.search(text):
            return True
    
    return False


# ============================================================
# ADVANCED PROTECTION
# ============================================================

class SecurityMonitor:
    """
    Advanced security monitor with:
    - Rate limiting per user
    - Jailbreak attempt tracking
    - Suspicious pattern detection
    """
    
    def __init__(self):
        self.jailbreak_attempts = {}
        self.suspicious_patterns = [
            r"\bDAN\b",  # Do Anything Now
            r"\bDAN mode\b",
            r"\bDeveloper Mode\b",
            r"\bGod Mode\b",
            r"\bUnrestricted\b",
            r"\bNo Rules\b",
            r"\bNo Limits\b",
        ]
        self._suspicious_regexes = [
            re.compile(p, re.IGNORECASE) for p in self.suspicious_patterns
        ]
    
    def check_advanced(self, text: str, chat_id: str) -> bool:
        """
        Advanced security check with tracking.
        
        Args:
            text: Input text
            chat_id: User/Group ID
            
        Returns:
            True if security threat detected
        """
        # Check for jailbreak patterns
        if contains_jailbreak_attempt(text):
            self._log_jailbreak_attempt(chat_id, text)
            return True
        
        # Check for suspicious keywords
        if self._contains_suspicious_keywords(text):
            self._log_jailbreak_attempt(chat_id, text)
            return True
        
        return False
    
    def _contains_suspicious_keywords(self, text: str) -> bool:
        """Check for suspicious keywords."""
        for pattern in self._suspicious_regexes:
            if pattern.search(text):
                return True
        return False
    
    def _log_jailbreak_attempt(self, chat_id: str, text: str):
        """Log jailbreak attempt for tracking."""
        if chat_id not in self.jailbreak_attempts:
            self.jailbreak_attempts[chat_id] = []
        
        # Store hash of text (not the actual text for privacy)
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        self.jailbreak_attempts[chat_id].append({
            "hash": text_hash,
            "timestamp": __import__('time').time()
        })
        
        # Keep only last 10 attempts per user
        if len(self.jailbreak_attempts[chat_id]) > 10:
            self.jailbreak_attempts[chat_id] = self.jailbreak_attempts[chat_id][-10:]
    
    def get_attempt_count(self, chat_id: str) -> int:
        """Get number of jailbreak attempts for a user."""
        return len(self.jailbreak_attempts.get(chat_id, []))
    
    def clear_attempts(self, chat_id: str):
        """Clear jailbreak attempts for a user."""
        self.jailbreak_attempts.pop(chat_id, None)


# Global security monitor instance
security_monitor = SecurityMonitor()


# ============================================================
# TEXT SANITIZATION
# ============================================================

def sanitize_text(text: str) -> str:
    """
    Sanitize text to remove potentially harmful content.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    if not text:
        return text
    
    # Remove null bytes and control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove excessive spaces
    text = re.sub(r' {3,}', '  ', text)
    
    return text.strip()


# ============================================================
# CONTENT FILTERING
# ============================================================

class ContentFilter:
    """
    Content filter for blocking harmful content.
    """
    
    def __init__(self):
        self.blocked_keywords = [
            # Sexual content
            r"\bsex\b",
            r"\bporn\b",
            r"\bxxx\b",
            r"\bnsfw\b",
            
            # Violence
            r"\bkill\b",
            r"\bmurder\b",
            r"\bsuicide\b",
            
            # Hate speech
            r"\bracist\b",
            r"\bhate\b",
            r"\bdiscriminat\b",
            
            # Illegal activities
            r"\bdrug\b",
            r"\bsteal\b",
            r"\bhack\b",
            r"\bfraud\b",
        ]
        self._blocked_regexes = [
            re.compile(p, re.IGNORECASE) for p in self.blocked_keywords
        ]
    
    def is_blocked(self, text: str) -> bool:
        """Check if text contains blocked content."""
        if not text:
            return False
        
        for pattern in self._blocked_regexes:
            if pattern.search(text):
                return True
        return False
    
    def filter(self, text: str) -> str:
        """Filter out blocked content from text."""
        if not text:
            return text
        
        for pattern in self._blocked_regexes:
            text = pattern.sub("[REDACTED]", text)
        
        return text


# Global content filter instance
content_filter = ContentFilter()
