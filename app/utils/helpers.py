import re
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    """Detect the language of the text"""
    try:
        # Simple language detection based on character sets
        hindi_chars = re.findall(r'[\u0900-\u097F]', text)
        english_chars = re.findall(r'[a-zA-Z]', text)
        
        if len(hindi_chars) > len(english_chars):
            return "hi"
        else:
            return "en"
    except Exception as e:
        logger.error(f"Error detecting language: {str(e)}")
        return "hi"  # Default to Hindi

def translate_text(text: str, target_language: str = "hi") -> str:
    """Translate text to target language"""
    try:
        # For now, return the original text
        # In production, integrate with Google Translate API
        if target_language == "hi" and detect_language(text) == "en":
            # Simple English to Hindi translations for common phrases
            translations = {
                "weather": "मौसम",
                "price": "कीमत",
                "crop": "फसल",
                "tomato": "टमाटर",
                "potato": "आलू",
                "onion": "प्याज",
                "wheat": "गेहूं",
                "rice": "चावल",
                "rain": "बारिश",
                "sunny": "धूप",
                "cloudy": "बादल",
                "temperature": "तापमान",
                "humidity": "आर्द्रता"
            }
            
            for eng, hin in translations.items():
                text = text.replace(eng, hin)
            
            return text
        else:
            return text
            
    except Exception as e:
        logger.error(f"Error translating text: {str(e)}")
        return text

def extract_location(text: str) -> Optional[str]:
    """Extract location from text with conservative parsing."""
    try:
        # 1) Prefer explicit state detection with word boundaries
        state_aliases = {
            'maharashtra': [r"maharashtra", r"महाराष्ट्र", r"mumbai", r"pune", r"nagpur"],
            'punjab': [r"punjab", r"पंजाब", r"ludhiana", r"amritsar", r"jalandhar", r"patiala"],
            'haryana': [r"haryana", r"हरियाणा", r"gurgaon", r"gurugram", r"faridabad", r"hisar", r"karnal", r"panipat", r"rohtak", r"ambala"],
            'uttar pradesh': [r"uttar\s+pradesh", r"उत्तर\s+प्रदेश", r"lucknow"],  # removed short 'up' alias
            'gujarat': [r"gujarat", r"गुजरात", r"ahmedabad", r"surat"],
            'rajasthan': [r"rajasthan", r"राजस्थान", r"jaipur", r"jodhpur"],
            'karnataka': [r"karnataka", r"कर्नाटक", r"bangalore", r"mysore"],
            'telangana': [r"telangana", r"तेलंगाना", r"hyderabad", r"warangal"],
            'tamil nadu': [r"tamil\s+nadu", r"तमिल\s+नाडु", r"chennai", r"coimbatore"],
        }
        tl = text.lower()
        for state, patterns in state_aliases.items():
            for pat in patterns:
                if re.search(rf"\b{pat}\b", tl):
                    return state

        # 2) Fallback: parse after location prepositions, but stop at conjunctions
        location_keywords = ["में", "in", "at", "near", "around", "से"]
        stop_tokens = {"and", "but", "or", "what", "are", "their", "prices", "price", "?", ",", "."}
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in location_keywords and i + 1 < len(words):
                tail = words[i+1: i+6]  # look ahead up to 5 tokens
                cleaned = []
                for w in tail:
                    pure = re.sub(r'[^\w\-\s]', '', w)
                    if pure.lower() in stop_tokens:
                        break
                    cleaned.append(pure)
                loc = " ".join(cleaned).strip()
                # If multi-word, try to map to a known state from within
                tl2 = loc.lower()
                for state, patterns in state_aliases.items():
                    for pat in patterns:
                        if re.search(rf"\b{pat}\b", tl2):
                            return state
                return loc or None

        return None
    except Exception as e:
        logger.error(f"Error extracting location: {str(e)}")
        return None

def extract_crop(text: str) -> Optional[str]:
    """Extract crop name from text"""
    try:
        # Common crop names in Hindi and English
        crops = {
            "गेहूं": "wheat", "wheat": "wheat",
            "चावल": "rice", "rice": "rice",
            "मक्का": "maize", "maize": "maize",
            "बाजरा": "bajra", "bajra": "bajra",
            "ज्वार": "jowar", "jowar": "jowar",
            "तिल": "sesame", "sesame": "sesame",
            "सरसों": "mustard", "mustard": "mustard",
            "मूंगफली": "groundnut", "groundnut": "groundnut",
            "कपास": "cotton", "cotton": "cotton",
            "गन्ना": "sugarcane", "sugarcane": "sugarcane",
            "टमाटर": "tomato", "tomato": "tomato",
            "आलू": "potato", "potato": "potato",
            "प्याज": "onion", "onion": "onion"
        }
        
        words = text.lower().split()
        for word in words:
            if word in crops:
                return crops[word]
        
        return None
    except Exception as e:
        logger.error(f"Error extracting crop: {str(e)}")
        return None

def format_response(response: str, language: str = "hi") -> str:
    """Format response for better readability"""
    try:
        # Add emojis and formatting based on content
        if "मौसम" in response or "weather" in response.lower():
            response = "🌦️ " + response
        elif "कीमत" in response or "price" in response.lower():
            response = "📊 " + response
        elif "समाचार" in response or "news" in response.lower():
            response = "📰 " + response
        elif "कीटनाशक" in response or "pesticide" in response.lower():
            response = "🧪 " + response
        elif "फसल" in response or "crop" in response.lower():
            response = "🌾 " + response
        
        return response
    except Exception as e:
        logger.error(f"Error formatting response: {str(e)}")
        return response

def sanitize_phone_number(phone_number: str) -> str:
    """Sanitize phone number for storage"""
    try:
        # Remove all non-digit characters
        cleaned = re.sub(r'[^\d]', '', phone_number)
        
        # Handle Indian phone numbers
        if cleaned.startswith('91') and len(cleaned) == 12:
            return cleaned
        elif len(cleaned) == 10:
            return '91' + cleaned
        else:
            return cleaned
    except Exception as e:
        logger.error(f"Error sanitizing phone number: {str(e)}")
        return phone_number

def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format"""
    try:
        cleaned = sanitize_phone_number(phone_number)
        return len(cleaned) >= 10
    except Exception as e:
        logger.error(f"Error validating phone number: {str(e)}")
        return False

def extract_location_and_crop(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract location and crop; prefer precise state alias detection."""
    try:
        location = extract_location(text)
        crop = extract_crop(text)
        return location, crop
    except Exception as e:
        logger.error(f"Error extracting location and crop: {str(e)}")
        return None, None 