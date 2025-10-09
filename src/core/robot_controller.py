import asyncio
import logging
import time
import signal
from typing import Optional
from src.services.tts.tts_service import TTSService
from src.services.speech.speech_recognizer import SpeechRecognizer
from src.services.llm.llm_service import LLMService

class RobotController:
    """Enhanced Robot Controller - SPEED OPTIMIZED for ERIK"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.conversation_active = False
        
        # Statistics tracking
        self.stats = {
            'messages_received': 0,
            'successful_transcriptions': 0,
            'failed_transcriptions': 0,
            'llm_responses': 0,
            'llm_failures': 0,
            'start_time': None
        }
        
        # Initialize services
        self.text_to_speech = TTSService(settings)
        self.speech_recognizer = SpeechRecognizer(settings)
        
        # Initialize LLM service
        try:
            self.llm_service = LLMService(settings)
            self.llm_enabled = True
            self.logger.info("🧠 LLM Service enabled - AI responses active!")
        except Exception as e:
            self.logger.warning(f"⚠️ LLM Service initialization failed: {e}")
            self.logger.info("   Robot will run without AI responses (echo mode)")
            self.llm_service = None
            self.llm_enabled = False
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        mode = "AI Conversations" if self.llm_enabled else "Echo Mode"
        self.logger.info(f"🤖 ERIK initialized - {mode}")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown on CTRL+C"""
        def signal_handler(signum, frame):
            self.logger.info("⏸️ Shutdown signal received...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start ERIK - FAST conversation mode"""
        self.is_running = True
        self.conversation_active = True
        self.stats['start_time'] = time.time()
        
        self.logger.info("🚀 ERIK starting...")
        
        # Quick greeting
        await self._speak_greeting()
        
        # Fast conversation loop
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while self.is_running and self.conversation_active:
            try:
                print("\n" + "="*60)
                print("🎤 Listening...")
                print("="*60)
                
                # Listen for voice input
                user_input = await self.speech_recognizer.listen(timeout=30)
                
                if user_input:
                    consecutive_failures = 0
                    self.stats['messages_received'] += 1
                    self.stats['successful_transcriptions'] += 1
                    
                    # Fast display
                    print(f"👤 You: {user_input}")
                    
                    # Check for exit
                    if self._is_exit_command(user_input):
                        await self._handle_exit()
                        break
                    
                    # Get AI response and speak FAST
                    await self._handle_conversation(user_input)
                    
                else:
                    self.stats['failed_transcriptions'] += 1
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"\n⚠️ {consecutive_failures} failures. Check mic!")
                        consecutive_failures = 0
                    else:
                        print("⚠️ No speech. Try again!")
                
                # Minimal delay
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                await self._handle_exit()
                break
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
                await asyncio.sleep(0.5)
        
        # Print stats
        self._print_final_stats()
        self.logger.info("✅ ERIK stopped!")
    
    async def _handle_conversation(self, user_input: str):
        """Handle conversation - ULTRA FAST!"""
        if not self.llm_enabled or self.llm_service is None:
            print(f"\n🤖 ERIK (Echo): {user_input}")
            return
        
        try:
            # Get AI response immediately
            start_time = time.time()
            ai_response = await self.llm_service.get_response(user_input, None)
            
            if ai_response:
                self.stats['llm_responses'] += 1
                elapsed = time.time() - start_time
                
                # Fast display
                print(f"🤖 ERIK ({elapsed:.1f}s): {ai_response}")
                
                # Speak immediately
                await self.text_to_speech.speak(ai_response)
                
            else:
                self.stats['llm_failures'] += 1
                print("❌ No response")
                
        except Exception as e:
            self.stats['llm_failures'] += 1
            self.logger.error(f"❌ Error: {e}")
    
    def _is_exit_command(self, text: str) -> bool:
        """Check for exit command"""
        exit_keywords = ['exit', 'quit', 'stop', 'goodbye', 'bye']
        return any(keyword in text.lower() for keyword in exit_keywords)
    
    async def _handle_exit(self):
        """Fast exit"""
        print("\n👋 Goodbye!")
        await self.text_to_speech.speak("Goodbye!")
        self.conversation_active = False
        self.is_running = False
    
    def _print_final_stats(self):
        """Print stats"""
        print("\n" + "="*60)
        print("📊 SESSION STATS")
        print("="*60)
        print(f"💬 Messages: {self.stats['messages_received']}")
        print(f"✅ Success: {self.stats['successful_transcriptions']}")
        print(f"❌ Failed: {self.stats['failed_transcriptions']}")
        
        if self.llm_enabled and self.llm_service:
            print(f"🧠 AI Responses: {self.stats['llm_responses']}")
            llm_stats = self.llm_service.get_stats()
            print(f"💰 Cost: ${llm_stats.get('estimated_cost', 0):.4f}")
        
        if self.stats['start_time']:
            duration = time.time() - self.stats['start_time']
            print(f"⏱️ Duration: {int(duration)}s")
        
        print("="*60 + "\n")
    
    async def _speak_greeting(self):
        """Quick greeting"""
        greeting = "Hey all, it's me ERIK!" if self.llm_enabled else "Hey all, it's me ERIK. Echo mode."
        self.logger.info(f"Speaking: {greeting}")
        await self.text_to_speech.speak(greeting)
        await asyncio.sleep(0.3)
    
    def stop(self):
        """Stop ERIK"""
        self.is_running = False
        self.conversation_active = False
        self.logger.info("🛑 Stopping...")
    
    def cleanup(self):
        """Cleanup"""
        self.logger.info("🧹 Cleaning up...")
        
        if hasattr(self, 'text_to_speech'):
            self.text_to_speech.cleanup()
        
        if hasattr(self, 'speech_recognizer'):
            self.speech_recognizer.cleanup()
        
        if hasattr(self, 'llm_service') and self.llm_service:
            self.llm_service.cleanup()
        
        self.logger.info("✅ Cleanup complete")
