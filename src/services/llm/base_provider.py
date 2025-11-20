from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers - makes it easy to add new LLMs"""
    
    def __init__(self, settings):
        self.settings = settings
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = settings.LLM_MAX_HISTORY
        
        # Statistics tracking
        self.stats = {
            'total_messages': 0,
            'total_tokens_used': 0,
            'conversations': 0,
            'errors': 0
        }
    
    @abstractmethod
    async def get_response(self, user_message: str, language: Optional[str] = None) -> Optional[str]:
        """
        Get AI response for user message
        
        Args:
            user_message: The user's input text
            language: Optional language code (e.g., 'en', 'ml')
        
        Returns:
            AI-generated response text or None if error
        """
        pass
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt that defines robot personality"""
        return self.settings.LLM_SYSTEM_PROMPT
    
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Trim history if too long
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation history"""
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.stats['conversations'] += 1
    
    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            **self.stats,
            'current_history_length': len(self.conversation_history)
        }
    
    def set_personality(self, personality: str):
        """Change robot personality"""
        self.system_prompt = personality
    
    @abstractmethod
    def cleanup(self):
        """Cleanup resources"""
        pass
