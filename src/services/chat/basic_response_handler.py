"""
Basic Response Handler
Handles common greetings and questions instantly without LLM
"""

import re
import logging
import random
from typing import Optional

class BasicResponseHandler:
    """
    Intercepts user input to provide instant responses for common phrases.
    Supports English and Malayalam (Manglish).
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define patterns and responses
        # Format: (regex_pattern, [list_of_possible_responses])
        self.patterns = [
            # --- MALAYALAM (Manglish) ---
            
            # Greetings
            (r'\b(sugam\s*aano|sugamano)\b', [
                "എനിക്ക് സുഖമാണ്! നിങ്ങൾക്ക് എങ്ങനെയുണ്ട്?",  # I am fine! How are you?
                "സുഖം തന്നെ. ചോദിച്ചതിന് നന്ദി!",           # Fine. Thanks for asking!
            ]),
            
            # Name
            (r'\b(endha\s*per|entha\s*peru|peru\s*entha)\b', [
                "എൻ്റെ പേര് ടോറസ്.",  # My name is Torres.
                "ഞാൻ ടോറസ്. നിങ്ങളുടെ AI സുഹൃത്ത്.", # I am Torres. Your AI friend.
            ]),
            
            # Food
            (r'\b(food\s*kayicho|kazhicho|kudicho)\b', [
                "ഞാൻ ഒരു റോബോട്ട് അല്ലേ? എനിക്ക് ഭക്ഷണം വേണ്ട, ചാർജ് മതി!", # I'm a robot, right? I don't need food, just charge!
                "റോബോട്ടുകൾ ഭക്ഷണം കഴിക്കില്ലല്ലോ. പക്ഷെ ബാറ്ററി ഫുൾ ആണ്!", # Robots don't eat food. But battery is full!
            ]),
            
            # General Malayalam Hello (if transcribed as English text)
            (r'\b(hello|hi)\s+kerala\b', [
                "നമസ്കാരം! എന്തൊക്കെയുണ്ട് വിശേഷം?",
            ]),

            # --- ENGLISH ---
            
            # Specific "Hello Torres" greeting (requested by user)
            (r'\bhello\s+torres\b', [
                "Hello! I am Torres, your AI friend.",
                "Hi there! I'm Torres.",
            ]),
            
            # General Greetings
            (r'^\s*(hello|hi|hey|greetings)\s*$', [
                "Hello! How can I help you?",
                "Hi there! Nice to meet you.",
                "Hey! What's up?",
            ]),
            
             (r'^\s*(hello|hi|hey)\s+torres\s*$', [
                "Hello! I am here.",
                "Hi! How can I help you?",
            ]),
            
            # Identity
            (r'\b(what\s*is\s*your\s*name|who\s*are\s*you)\b', [
                "My name is Torres.",
                "I am Torres, your AI robot assistant.",
            ]),
            
            (r'\b(how\s*are\s*you)\b', [
                "I'm doing great, thanks for asking!",
                "I'm fine! Systems are running perfectly.",
            ]),
        ]
        
        self.logger.info("✅ Basic Response Handler initialized")

    def get_response(self, text: str) -> Optional[str]:
        """
        Check if text matches any pattern and return a response.
        Returns None if no match found.
        """
        if not text:
            return None
            
        text_lower = text.lower().strip()
        
        for pattern, responses in self.patterns:
            if re.search(pattern, text_lower):
                response = random.choice(responses)
                self.logger.info(f"⚡ Basic Response triggered: '{text}' -> '{response}'")
                return response
                
        return None
