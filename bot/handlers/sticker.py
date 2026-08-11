"""
Sticker Message Handler
======================

Handles sticker messages from Zalo.
Provides natural responses to stickers.
"""

import random
from typing import Optional


# ============================================================
# STICKER HANDLER
# ============================================================

class StickerHandler:
    """Handles sticker messages with natural responses."""
    
    def __init__(self):
        # Sticker responses categorized by type
        self._sticker_responses = {
            # Like/Thumbs up
            "like": [
                "Cute quá 😍",
                "Thích lắm 👍",
                "Hay đó 😂",
                "Đẹp quá 😊",
                "Tuyệt vời 👌",
            ],
            # Love/Heart
            "love": [
                "Yêu quá 💖",
                "Thương lắm 😘",
                "Tuyệt vời 🥰",
                "Rất đáng yêu 💕",
                "Trái tim nở hoa 🌸",
            ],
            # Laugh/Haha
            "haha": [
                "Haha 😂",
                "Cười bò 🤣",
                "Vui quá 😆",
                "Buồn cười 😂",
                "Cười không ngừng được 🤣",
            ],
            # Sad/Cry
            "sad": [
                "Đừng buồn 😢",
                "Có chuyện gì thế? 😔",
                "Mình ở đây 💙",
                "Mọi chuyện sẽ ổn thôi 😌",
                "Cứ nói ra đi, mình nghe 🥺",
            ],
            # Angry
            "angry": [
                "Đừng tức giận 😠",
                "Bình tĩnh nha 😐",
                "Mọi chuyện sẽ ổn thôi 😌",
                "Thở sâu đi 🧘",
                "Mình hiểu mà 😔",
            ],
            # Surprise
            "surprise": [
                "Ngạc nhiên quá 😮",
                "Wow! 😲",
                "Không ngờ 😳",
                "Thật không? 😲",
                "Bất ngờ 😱",
            ],
            # Default/Unknown
            "default": [
                "Sticker cute 😊",
                "Hay đó 👍",
                "Vui quá 😄",
                "Thú vị 😆",
                "Đẹp lắm 😍",
            ],
        }
    
    def handle(
        self,
        chat_id: str,
        sticker_id: str = "",
        sticker_category: str = ""
    ) -> str:
        """
        Handle a sticker message and return a response.
        
        Args:
            chat_id: Chat ID (for context)
            sticker_id: Sticker ID (if available)
            sticker_category: Sticker category (like, love, haha, etc.)
            
        Returns:
            Response text
        """
        # Determine the best response category
        category = self._determine_category(sticker_category, sticker_id)
        
        # Get random response from the category
        responses = self._sticker_responses.get(category, self._sticker_responses["default"])
        return random.choice(responses)
    
    def _determine_category(self, category: str, sticker_id: str) -> str:
        """
        Determine the best response category based on sticker info.
        
        Args:
            category: Sticker category from Zalo
            sticker_id: Sticker ID
            
        Returns:
            Response category
        """
        # Normalize category
        if not category:
            return "default"
        
        category_lower = category.lower()
        
        # Map Zalo sticker categories to our response categories
        category_mapping = {
            "thumbs_up": "like",
            "like": "like",
            "heart": "love",
            "love": "love",
            "laugh": "haha",
            "haha": "haha",
            "joy": "haha",
            "smile": "default",
            "sad": "sad",
            "cry": "sad",
            "tears": "sad",
            "angry": "angry",
            "rage": "angry",
            "surprise": "surprise",
            "shock": "surprise",
        }
        
        return category_mapping.get(category_lower, "default")


# Global instance
sticker_handler = StickerHandler()
