"""
OCR Module - Text Extraction from Images
=========================================

This module provides OCR capabilities for extracting text from images.
Supports multiple OCR providers:
- EasyOCR (offline, easy to use)
- Tesseract (offline, requires installation)
- Google Vision API (online, most accurate)
"""

import re
import base64
import requests
import numpy as np
from io import BytesIO
from PIL import Image
from typing import Optional, List, Tuple
from pathlib import Path

from bot.config import (
    OCR_PROVIDER,
    GOOGLE_VISION_API_KEY,
)


# ============================================================
# OCR PROVIDER BASE CLASS
# ============================================================

class OCRProvider:
    """Base class for OCR providers."""
    
    def extract_text(self, image_url: str) -> Optional[str]:
        """
        Extract text from an image URL.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Extracted text or None if failed
        """
        raise NotImplementedError
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """
        Extract text from raw image bytes.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Extracted text or None if failed
        """
        raise NotImplementedError


# ============================================================
# EASYOCR PROVIDER (Default)
# ============================================================

class EasyOCRProvider(OCRProvider):
    """
    EasyOCR provider - offline OCR with good accuracy.
    Requires: pip install easyocr
    """
    
    def __init__(self, lang: str = "vi,en"):
        self.lang = lang
        self._reader = None
    
    def _get_reader(self):
        """Lazy load EasyOCR reader."""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader([self.lang])
            except ImportError:
                raise RuntimeError(
                    "EasyOCR not installed. Please run: pip install easyocr"
                )
        return self._reader
    
    def extract_text(self, image_url: str) -> Optional[str]:
        """Extract text from image URL using EasyOCR."""
        try:
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image_bytes = response.content
            
            return self.extract_text_from_bytes(image_bytes)
        except Exception as e:
            print(f"EasyOCR download error: {e}")
            return None
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """Extract text from image bytes using EasyOCR."""
        try:
            reader = self._get_reader()
            
            # Convert bytes to numpy array
            image = Image.open(BytesIO(image_bytes))
            image_np = np.array(image)
            
            # Perform OCR
            results = reader.readtext(image_np)
            
            # Combine all detected text
            extracted_text = "\n".join([result[1] for result in results])
            
            return extracted_text if extracted_text else None
        except Exception as e:
            print(f"EasyOCR extraction error: {e}")
            return None


# ============================================================
# TESSERACT PROVIDER
# ============================================================

class TesseractOCRProvider(OCRProvider):
    """
    Tesseract OCR provider - offline OCR.
    Requires: pip install pytesseract and tesseract-ocr installed on system
    """
    
    def __init__(self, lang: str = "vie+eng"):
        self.lang = lang
    
    def extract_text(self, image_url: str) -> Optional[str]:
        """Extract text from image URL using Tesseract."""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image_bytes = response.content
            
            return self.extract_text_from_bytes(image_bytes)
        except Exception as e:
            print(f"Tesseract download error: {e}")
            return None
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """Extract text from image bytes using Tesseract."""
        try:
            import pytesseract
            
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang=self.lang)
            
            return text if text.strip() else None
        except ImportError:
            raise RuntimeError(
                "Tesseract not installed. Please run: pip install pytesseract "
                "and install tesseract-ocr on your system."
            )
        except Exception as e:
            print(f"Tesseract extraction error: {e}")
            return None


# ============================================================
# GOOGLE VISION PROVIDER
# ============================================================

class GoogleVisionProvider(OCRProvider):
    """
    Google Vision API provider - online OCR with high accuracy.
    Requires: GOOGLE_VISION_API_KEY in environment
    """
    
    API_URL = "https://vision.googleapis.com/v1/images:annotate"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def extract_text(self, image_url: str) -> Optional[str]:
        """Extract text from image URL using Google Vision."""
        try:
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image_bytes = response.content
            
            return self.extract_text_from_bytes(image_bytes)
        except Exception as e:
            print(f"Google Vision download error: {e}")
            return None
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """Extract text from image bytes using Google Vision."""
        if not self.api_key:
            print("Google Vision API key not configured")
            return None
        
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Prepare request
            payload = {
                "requests": [
                    {
                        "image": {"content": image_base64},
                        "features": [
                            {"type": "TEXT_DETECTION"}
                        ]
                    }
                ]
            }
            
            # Make API request
            response = requests.post(
                f"{self.API_URL}?key={self.api_key}",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract text from response
            if "responses" in data and len(data["responses"]) > 0:
                text_annotations = data["responses"][0].get("fullTextAnnotation", {})
                extracted_text = text_annotations.get("text", "")
                
                return extracted_text if extracted_text else None
            
            return None
        except Exception as e:
            print(f"Google Vision API error: {e}")
            return None


# ============================================================
# OCR MANAGER
# ============================================================

class OCRManager:
    """
    Manages OCR providers and provides a unified interface.
    """
    
    def __init__(self):
        self.provider = self._get_provider()
    
    def _get_provider(self) -> OCRProvider:
        """Get the configured OCR provider."""
        if OCR_PROVIDER == "google_vision":
            if not GOOGLE_VISION_API_KEY:
                print("Google Vision API key not configured, falling back to EasyOCR")
                return EasyOCRProvider()
            return GoogleVisionProvider(GOOGLE_VISION_API_KEY)
        elif OCR_PROVIDER == "tesseract":
            return TesseractOCRProvider()
        else:
            # Default to EasyOCR
            return EasyOCRProvider()
    
    def extract_text(self, image_url: str) -> Optional[str]:
        """
        Extract text from an image URL using the configured provider.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Extracted text or None if failed
        """
        return self.provider.extract_text(image_url)
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """
        Extract text from raw image bytes using the configured provider.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Extracted text or None if failed
        """
        return self.provider.extract_text_from_bytes(image_bytes)
    
    def clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted text by removing artifacts and normalizing.
        
        Args:
            text: Extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters
        text = re.sub(r'[^\x20-\x7E\u00A0-\u02AF\u1EA0-\u1EF9]', '', text)
        
        # Normalize Vietnamese characters
        text = self._normalize_vietnamese(text)
        
        return text.strip()
    
    def _normalize_vietnamese(self, text: str) -> str:
        """Normalize Vietnamese text (convert common OCR errors)."""
        # Common OCR errors for Vietnamese
        replacements = {
            # Lowercase
            r'[àáâãăạằắẵặẳ]': 'a',
            r'[èéêẹẽềếễệể]': 'e',
            r'[ìíîĩị]': 'i',
            r'[òóôõọồốỗộổ]': 'o',
            r'[ùúûũụ]': 'u',
            r'[ỳýỷỹỵ]': 'y',
            r'[đ]': 'd',
            
            # Uppercase
            r'[ÀÁÂÃĂẠẰẮẴẶẲ]': 'A',
            r'[ÈÉÊẸẼỀẾỄỆỂ]': 'E',
            r'[ÌÍÎĨỊ]': 'I',
            r'[ÒÓÔÕỌỒỐỖỘỔ]': 'O',
            r'[ÙÚÛŨỤ]': 'U',
            r'[ỲÝỶỸỴ]': 'Y',
            r'[Đ]': 'D',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text


# ============================================================
# TEXT DETECTION IN IMAGES
# ============================================================

class ImageTextDetector:
    """
    Detects and extracts text from images, with jailbreak detection.
    """
    
    def __init__(self):
        self.ocr = OCRManager()
        from bot.utils.security import contains_jailbreak_attempt
        self.contains_jailbreak = contains_jailbreak_attempt
    
    async def check_image_for_jailbreak(self, image_url: str) -> Tuple[bool, Optional[str]]:
        """
        Check if an image contains jailbreak attempts in its text.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Tuple of (is_jailbreak, extracted_text)
        """
        # Extract text from image
        extracted_text = self.ocr.extract_text(image_url)
        
        if not extracted_text:
            return False, None
        
        # Clean the text
        cleaned_text = self.ocr.clean_extracted_text(extracted_text)
        
        # Check for jailbreak attempts
        is_jailbreak = self.contains_jailbreak(cleaned_text)
        
        return is_jailbreak, cleaned_text
    
    async def get_image_text(self, image_url: str) -> Optional[str]:
        """
        Get clean text from an image.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Extracted and cleaned text, or None if failed
        """
        extracted_text = self.ocr.extract_text(image_url)
        if not extracted_text:
            return None
        return self.ocr.clean_extracted_text(extracted_text)


# Global instances
ocr_manager = OCRManager()
text_detector = ImageTextDetector()
