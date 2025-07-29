import asyncio
import logging
import time
from typing import Optional
from src.services.speech.text_to_speech import TextToSpeech
from src.services.speech.speech_recognizer import SpeechRecognizer

class RobotController:
    """Robot controller - Step 2: Speaking + Voice Recording"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        
        # Step 2: Initialize BOTH services
        self.text_to_speech = TextToSpeech(settings)
        self.speech_recognizer = SpeechRecognizer(settings)
        
        # Future steps will add:
        # self.llm_service = LLMService(settings)
        # self.conversation_manager = ConversationManager(self.llm_service)
        
        self.logger.info("Robot Controller initialized (Step 2: Speaking + Recording)")
    
    async def start(self):
        """Start the robot - Step 2: Speak greeting then listen"""
        self.is_running = True
        self.logger.info("Robot starting Step 2...")
        
        # Step 2: Speak greeting
        await self._speak_greeting()
        
        # Step 2: Voice recording loop
        while self.is_running:
            try:
                print("\n" + "="*50)
                print("STEP 2: Voice Recording Test")
                print("="*50)
                
                # Listen for voice input
                user_input = await self.speech_recognizer.listen(timeout=30)
                
                if user_input:
                    # Just console output - no processing yet!
                    print(f"\n🎤 RECORDED: '{user_input}'")
                    print(f"⏱️  TIME: {time.strftime('%H:%M:%S')}")
                    print(f"📏 LENGTH: {len(user_input)} characters")
                    print(f"🔤 WORDS: {len(user_input.split())} words")
                    print("-" * 50)
                    
                    # Check for exit
                    if "exit" in user_input.lower() or "quit" in user_input.lower():
                        print("👋 Goodbye!")
                        break
                else:
                    print("No speech detected. Try again!")
                
                # Small delay
                await asyncio.sleep(0.5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Error: {e}")
                await asyncio.sleep(1)
        
        self.logger.info("Step 2 complete!")
    
    async def _speak_greeting(self):
        """Speak initial greeting"""
        greeting = "Hello! I am your robot. Step 2 is ready - I can speak AND listen! Try saying something!"
        self.logger.info(f"Speaking: {greeting}")
        await self.text_to_speech.speak(greeting)
        
        # Give user a moment
        await asyncio.sleep(1)
    
    def stop(self):
        """Stop the robot"""
        self.is_running = False
        self.logger.info("Robot stopping...")
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'text_to_speech'):
            self.text_to_speech.cleanup()
        if hasattr(self, 'speech_recognizer'):
            self.speech_recognizer.cleanup()
