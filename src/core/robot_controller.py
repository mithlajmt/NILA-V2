import asyncio
import logging
from typing import Optional
from src.services.speech.text_to_speech import TextToSpeech

class RobotController:
    """Robot controller - Step 1: Just speaking greeting"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        
        # Step 1: Initialize ONLY text-to-speech
        self.text_to_speech = TextToSpeech(settings)
        
        # Future steps will add:
        # self.speech_recognizer = SpeechRecognizer(settings)
        # self.llm_service = LLMService(settings)
        # self.conversation_manager = ConversationManager(self.llm_service)
        
        self.logger.info("🤖 Robot Controller initialized (Step 1: Speaking only)")
    
    async def start(self):
        """Start the robot - Step 1: Just speak greeting"""
        self.is_running = True
        self.logger.info("🚀 Robot starting Step 1...")
        
        # Step 1: Just speak greeting and exit
        await self._speak_greeting()
        
        self.logger.info("✅ Step 1 complete! Robot spoke greeting successfully.")
        
        # Future steps will add the main listening loop here:
        # while self.is_running:
        #     user_input = await self.speech_recognizer.listen()
        #     response = await self._process_conversation(user_input)
        #     await self.text_to_speech.speak(response)
    
    async def _speak_greeting(self):
        """Speak initial greeting"""
        greeting = "Hello! I am your robot assistant. Step 1 is working perfectly - I can speak!"
        await self.text_to_speech.speak(greeting)
    
    def stop(self):
        """Stop the robot"""
        self.is_running = False
        self.logger.info("🛑 Robot stopping...")
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'text_to_speech'):
            self.text_to_speech.cleanup()
