"""
AI Handler - Mistral API Integration
====================================

Handles all AI API calls with:
- Automatic retry on failure
- Token usage tracking
- Error handling
"""

import asyncio
import httpx
import json
from typing import Tuple, List, Dict, Any, Optional

from bot.config import (
    MISTRAL_API_KEY,
    MISTRAL_URL,
    MODEL,
)


# ============================================================
# AI CLIENT
# ============================================================

class AIClient:
    """
    Client for calling Mistral AI API.
    """
    
    def __init__(self):
        self._client = None
        self._retry_count = 3
        self._retry_delay = 1
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def call_mistral(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1200,
        temperature: float = 0.7,
        model: str = MODEL
    ) -> Tuple[str, int]:
        """
        Call Mistral API with retry logic.
        
        Args:
            messages: List of messages for the AI
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
            model: Model to use
            
        Returns:
            Tuple of (response_text, tokens_used)
            
        Raises:
            Exception: If all retries fail
        """
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        last_exception = None
        
        for attempt in range(self._retry_count):
            try:
                client = self._get_client()
                response = await client.post(
                    MISTRAL_URL,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    tokens_used = data.get("usage", {}).get("total_tokens", 0)
                    return content, tokens_used
                
                elif response.status_code == 429:  # Rate limited
                    if attempt < self._retry_count - 1:
                        await asyncio.sleep(self._retry_delay * (attempt + 1))
                        continue
                
                elif response.status_code == 401:  # Unauthorized
                    raise RuntimeError("Invalid Mistral API key")
                
                else:
                    response.raise_for_status()
                    
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                    continue
            except Exception as e:
                last_exception = e
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                    continue
        
        # All retries failed
        if last_exception:
            raise last_exception
        
        raise RuntimeError("Failed to call Mistral API after all retries")


# ============================================================
# SIMPLE FUNCTION WRAPPER
# ============================================================

# Global AI client instance
ai_client = AIClient()


async def call_mistral(
    messages: List[Dict[str, Any]],
    max_tokens: int = 1200,
    temperature: float = 0.7,
    model: str = MODEL
) -> Tuple[str, int]:
    """
    Simple function wrapper for calling Mistral API.
    
    Args:
        messages: List of messages for the AI
        max_tokens: Maximum tokens to generate
        temperature: Temperature for sampling
        model: Model to use
        
    Returns:
        Tuple of (response_text, tokens_used)
    """
    return await ai_client.call_mistral(
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
        model=model
    )


# ============================================================
# ALTERNATIVE AI PROVIDERS (Optional)
# ============================================================

class AlternativeAIProvider:
    """
    Base class for alternative AI providers.
    Can be extended for other AI services (Grok, Claude, etc.)
    """
    
    async def call(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1200,
        temperature: float = 0.7
    ) -> Tuple[str, int]:
        """
        Call the AI provider.
        
        Args:
            messages: List of messages
            max_tokens: Maximum tokens
            temperature: Temperature
            
        Returns:
            Tuple of (response_text, tokens_used)
        """
        raise NotImplementedError


# ============================================================
# FALLBACK AI (if Mistral fails)
# ============================================================

class FallbackAI:
    """
    Fallback AI responses when primary AI fails.
    """
    
    @staticmethod
    def get_fallback_response(message_type: str = "text") -> str:
        """
        Get a fallback response based on message type.
        
        Args:
            message_type: Type of message (text, image, sticker)
            
        Returns:
            Fallback response text
        """
        responses = {
            "text": [
                "Mình đang gặp chút trục trặc 😅 Thử lại giúp mình nha.",
                "Hệ thống đang bận, bạn chờ xíu nha 😅",
                "Mình chưa nghĩ ra gì 😅",
            ],
            "image": [
                "Mình chưa nhìn rõ ảnh này 😅",
                "Ảnh này hơi khó, bạn gửi lại giúp mình nha 😅",
                "Mình chưa xử lý được ảnh này 😅",
            ],
            "sticker": [
                "Sticker cute 😊",
                "Hay đó 👍",
                "Vui quá 😄",
            ],
        }
        
        import random
        return random.choice(responses.get(message_type, responses["text"]))
