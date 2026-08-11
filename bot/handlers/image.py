"""
Image Message Handler
=====================

Handles image messages from Zalo, including:
- Regular images
- Images with captions
- Jailbreak detection in images (OCR)
- Sticker messages (if supported by Zalo API)
"""

import asyncio
from typing import Optional, Dict, Any, Tuple

from bot.config import (
    MAX_MESSAGES,
    SUMMARY_TRIGGER,
    MAX_TOKENS,
    TEMPERATURE,
    BAN_MESSAGE,
)
from bot.utils.security import (
    contains_jailbreak_attempt,
    security_monitor,
)
from bot.utils.memory import memory_manager
from bot.utils.stats import stats_manager
from bot.utils.ocr import text_detector


# ============================================================
# IMAGE HANDLER
# ============================================================

class ImageHandler:
    """Handles image messages."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
    
    async def handle(
        self,
        chat_id: str,
        image_url: str,
        caption: str = "",
        bot: Any = None
    ) -> Optional[str]:
        """
        Handle an image message.
        
        Args:
            chat_id: Chat ID
            image_url: URL of the image
            caption: Image caption (if any)
            bot: Zalo bot instance (optional, for sending messages)
            
        Returns:
            Response text or None
        """
        # Check caption for jailbreak attempts first
        if caption:
            if contains_jailbreak_attempt(caption):
                from bot.utils.security import ban_user
                ban_user(chat_id, reason="prompt injection / jailbreak (caption)")
                return BAN_MESSAGE
            
            # Advanced security check on caption
            if security_monitor.check_advanced(caption, chat_id):
                from bot.utils.security import ban_user
                ban_user(chat_id, reason="prompt injection / jailbreak (caption advanced)")
                return BAN_MESSAGE
        
        # Check image for jailbreak attempts using OCR
        is_jailbreak, extracted_text = await text_detector.check_image_for_jailbreak(image_url)
        if is_jailbreak:
            from bot.utils.security import ban_user
            ban_user(chat_id, reason=f"prompt injection / jailbreak (image OCR: {extracted_text[:50]}...)")
            return BAN_MESSAGE
        
        # Build content for memory
        content = []
        
        # Add caption if exists
        if caption:
            content.append({
                "type": "text",
                "text": caption
            })
        else:
            # Default prompt for images without caption
            content.append({
                "type": "text",
                "text": "Hãy xem ảnh này và mô tả nội dung chính cho mình."
            })
        
        # Add image
        content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
        
        # Add to memory
        await memory_manager.add_user_message(chat_id, content)
        
        # Check if context needs compression
        context = await memory_manager.short_term.get_context(chat_id)
        if len(context) >= SUMMARY_TRIGGER:
            await self._compress_context(chat_id)
        
        # Build messages for AI
        messages = await memory_manager.build_messages(
            chat_id,
            self._get_system_prompt()
        )
        
        # Call AI
        try:
            reply, tokens_used = await self._call_ai(messages)
            
            if not reply:
                reply = "Mình chưa nhìn rõ ảnh này 😅"
            
            # Add assistant response to memory
            await memory_manager.add_assistant_message(chat_id, reply)
            
            # Record statistics
            await stats_manager.record_user_message(
                chat_id,
                tokens_used,
                "image"
            )
            
            # Update long-term memory periodically
            if len(context) % 10 == 0:
                await self._update_long_term_memory(chat_id)
            
            return reply
            
        except Exception as e:
            print(f"Vision AI call error: {e}")
            return "Mình chưa xử lý được ảnh này 😅 Bạn thử gửi lại nha."
    
    async def _compress_context(self, chat_id: str):
        """Compress conversation context."""
        from bot.utils.memory import memory_manager
        
        async def summarizer(old_messages: list) -> str:
            """Generate summary of old messages."""
            import json
            
            summary_messages = [
                {
                    "role": "system",
                    "content": """
                    Bạn là hệ thống quản lý memory cho Bringh.
                    
                    Hãy tóm tắt phần hội thoại cũ.
                    
                    CHỈ giữ:
                    - Tên người dùng nếu có
                    - Người/vật quan trọng
                    - Sở thích hoặc thông tin cơ bản
                    - Chủ đề đang nói
                    - Những việc quan trọng
                    - Câu hỏi chưa được giải quyết
                    - Thông tin có thể cần dùng lại sau này
                    
                    Bỏ:
                    - Lời chào
                    - Nội dung lặp lại
                    - Câu nói vô nghĩa
                    - Chi tiết không quan trọng
                    
                    Không tự thêm thông tin.
                    Viết ngắn gọn bằng tiếng Việt.
                    """
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        old_messages,
                        ensure_ascii=False,
                        default=str
                    )
                }
            ]
            
            try:
                from bot.handlers.ai import call_mistral
                summary, tokens_used = await call_mistral(
                    summary_messages,
                    max_tokens=1000,
                    temperature=0.2
                )
                await stats_manager.record_system_tokens(
                    tokens_used,
                    "context_compression"
                )
                return summary
            except Exception as e:
                print(f"Summary error: {e}")
                return "Cuộc trò chuyện trước đó."
        
        await memory_manager.short_term.compress_context(
            chat_id,
            summarizer
        )
        
        # Also update long-term memory
        await self._update_long_term_memory(chat_id)
    
    async def _update_long_term_memory(self, chat_id: str):
        """Update long-term memory from recent context."""
        async def extractor(new_messages: list, existing_facts: str) -> str:
            """Extract facts from messages."""
            import json
            
            extract_messages = [
                {
                    "role": "system",
                    "content": """
                    Bạn là hệ thống trích xuất trí nhớ dài hạn cho Bringh - một
                    người bạn AI luôn muốn nhớ về người mình trò chuyện cùng, giống
                    như một người bạn thật sự.
                    
                    Nhiệm vụ: đọc "TRÍ NHỚ ĐÃ CÓ" và "HỘI THOẠI MỚI", rồi trả về một
                    bản TRÍ NHỚ DÀI HẠN đã cập nhật, gộp thông tin cũ + mới, viết lại
                    ngắn gọn, không trùng lặp.
                    
                    CHỈ giữ những điều đáng nhớ lâu dài, ví dụ:
                    - Tên, biệt danh, cách xưng hô người dùng thích
                    - Sở thích, thói quen, tính cách
                    - Công việc, học tập, hoàn cảnh sống (nếu họ tự kể)
                    - Những người/thú cưng/sự kiện quan trọng với họ
                    - Những chuyện đang diễn ra trong đời họ mà một người bạn nên nhớ
                    
                    KHÔNG giữ:
                    - Câu hỏi vặt, chuyện phiếm không có giá trị lâu dài
                    - Nội dung chỉ liên quan một lần, không cần nhớ về sau
                    - Bất cứ điều gì không chắc chắn hoặc do bạn tự suy đoán
                    
                    Không tự bịa thêm thông tin không có trong hội thoại.
                    Viết dạng gạch đầu dòng ngắn gọn, bằng tiếng Việt.
                    Nếu không có gì đáng nhớ thêm, giữ nguyên trí nhớ cũ (hoặc trả
                    về chuỗi rỗng nếu trí nhớ cũ cũng rỗng và không có gì mới).
                    """
                },
                {
                    "role": "user",
                    "content": (
                        "TRÍ NHỚ ĐÃ CÓ:\n"
                        + (existing_facts or "(chưa có gì)")
                        + "\n\nHỘI THOẠI MỚI:\n"
                        + json.dumps(
                            new_messages,
                            ensure_ascii=False,
                            default=str
                        )
                    )
                }
            ]
            
            try:
                from bot.handlers.ai import call_mistral
                updated_facts, tokens_used = await call_mistral(
                    extract_messages,
                    max_tokens=600,
                    temperature=0.2
                )
                await stats_manager.record_system_tokens(
                    tokens_used,
                    "long_term_memory"
                )
                return updated_facts
            except Exception as e:
                print(f"Long-term memory error: {e}")
                return existing_facts
        
        context = await memory_manager.short_term.get_context(chat_id)
        if context:
            await memory_manager.update_long_term(
                chat_id,
                extractor
            )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for Bringh (same as text handler)."""
        from bot.handlers.text import TextHandler
        return TextHandler()._get_system_prompt()
    
    async def _call_ai(
        self,
        messages: list,
        max_tokens: int = MAX_TOKENS,
        temperature: float = TEMPERATURE
    ) -> Tuple[str, int]:
        """Call AI API (Mistral Vision)."""
        from bot.handlers.ai import call_mistral
        return await call_mistral(messages, max_tokens, temperature)


# ============================================================
# STICKER HANDLER
# ============================================================

class StickerHandler:
    """Handles sticker messages (if supported by Zalo API)."""
    
    def __init__(self):
        self._sticker_responses = {
            # Common sticker categories
            "like": ["Cute quá 😍", "Thích lắm 👍", "Hay đó 😂"],
            "love": ["Yêu quá 💖", "Thương lắm 😘", "Tuyệt vời 🥰"],
            "haha": ["Haha 😂", "Cười bò 🤣", "Vui quá 😆"],
            "sad": ["Đừng buồn 😢", "Có chuyện gì thế? 😔", "Mình ở đây 💙"],
            "angry": ["Đừng tức giận 😠", "Bình tĩnh nha 😐", "Mọi chuyện sẽ ổn thôi 😌"],
            "default": ["Sticker cute 😊", "Hay đó 👍", "Vui quá 😄"],
        }
    
    async def handle(
        self,
        chat_id: str,
        sticker_id: str = "",
        sticker_category: str = ""
    ) -> str:
        """
        Handle a sticker message.
        
        Args:
            chat_id: Chat ID
            sticker_id: Sticker ID (if available)
            sticker_category: Sticker category (like, love, haha, etc.)
            
        Returns:
            Response text
        """
        # Determine response based on sticker category
        if sticker_category and sticker_category in self._sticker_responses:
            import random
            return random.choice(self._sticker_responses[sticker_category])
        
        # Default response
        import random
        return random.choice(self._sticker_responses["default"])


# Global instances
image_handler = ImageHandler()
sticker_handler = StickerHandler()
