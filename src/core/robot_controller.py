import asyncio
import logging
import time
import signal
from typing import Optional
from src.services.speech.text_to_speech import TextToSpeech
from src.services.speech.speech_recognizer import SpeechRecognizer

class RobotController:
    """Enhanced Robot Controller - Step 2: Speaking + Voice Recording with improvements"""
    
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
            'start_time': None
        }
        
        # Step 2: Initialize BOTH services
        self.text_to_speech = TextToSpeech(settings)
        self.speech_recognizer = SpeechRecognizer(settings)
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Future steps will add:
        # self.llm_service = LLMService(settings)
        # self.conversation_manager = ConversationManager(self.llm_service)
        
        self.logger.info("🤖 Enhanced Robot Controller initialized (Step 2: Speaking + Recording)")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown on CTRL+C"""
        def signal_handler(signum, frame):
            self.logger.info("⏸️ Shutdown signal received...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the robot - Step 2: Speak greeting then listen"""
        self.is_running = True
        self.conversation_active = True
        self.stats['start_time'] = time.time()
        
        self.logger.info("🚀 Robot starting Step 2...")
        
        # Step 2: Speak greeting
        await self._speak_greeting()
        
        # Step 2: Enhanced voice recording loop
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while self.is_running and self.conversation_active:
            try:
                self._print_status_header()
                
                # Listen for voice input
                user_input = await self.speech_recognizer.listen(timeout=30)
                
                if user_input:
                    consecutive_failures = 0  # Reset failure counter
                    self.stats['messages_received'] += 1
                    self.stats['successful_transcriptions'] += 1
                    
                    # Display recorded message with analysis
                    self._display_message_info(user_input)
                    
                    # Check for exit commands
                    if self._is_exit_command(user_input):
                        await self._handle_exit()
                        break
                    
                    # Acknowledge receipt
                    await self._acknowledge_message()
                    
                else:
                    self.stats['failed_transcriptions'] += 1
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"\n⚠️ {consecutive_failures} consecutive failures. Check microphone!")
                        await self.text_to_speech.speak("I'm having trouble hearing you. Please check your microphone.")
                        consecutive_failures = 0
                    else:
                        print("⚠️ No speech detected. Try again!")
                
                # Small delay between attempts
                await asyncio.sleep(0.3)
                
            except KeyboardInterrupt:
                await self._handle_exit()
                break
            except Exception as e:
                self.logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(1)
        
        # Print final statistics
        self._print_final_stats()
        self.logger.info("✅ Step 2 complete!")
    
    def _print_status_header(self):
        """Print status header for each listening cycle"""
        print("\n" + "="*60)
        print("🎯 ROBOT LISTENING MODE")
        print("="*60)
        print(f"💬 Messages received: {self.stats['messages_received']}")
        print(f"✅ Successful: {self.stats['successful_transcriptions']} | ❌ Failed: {self.stats['failed_transcriptions']}")
        if self.stats['start_time']:
            uptime = time.time() - self.stats['start_time']
            print(f"⏱️  Uptime: {int(uptime)}s")
        print("-" * 60)
    
    def _display_message_info(self, text: str):
        """Display detailed information about the received message"""
        print(f"\n🎤 RECEIVED MESSAGE:")
        print(f"  📝 Text: '{text}'")
        print(f"  ⏱️  Time: {time.strftime('%H:%M:%S')}")
        print(f"  📏 Length: {len(text)} characters")
        print(f"  🔤 Words: {len(text.split())} words")
        print(f"  🔢 Message #: {self.stats['messages_received']}")
        print("-" * 60)
    
    def _is_exit_command(self, text: str) -> bool:
        """Check if the text contains an exit command"""
        exit_keywords = ['exit', 'quit', 'stop', 'goodbye', 'bye']
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in exit_keywords)
    
    async def _handle_exit(self):
        """Handle graceful exit"""
        print("\n" + "="*60)
        print("👋 Goodbye! Shutting down...")
        print("="*60)
        await self.text_to_speech.speak("Goodbye! Thank you for talking with me.")
        self.conversation_active = False
        self.is_running = False
    
    async def _acknowledge_message(self):
        """Acknowledge that message was received (optional feedback)"""
        # For now, just a visual confirmation
        # In Step 3, this will be replaced with LLM response
        print("✅ Message received and logged!")
    
    def _print_final_stats(self):
        """Print final statistics before shutdown"""
        print("\n" + "="*60)
        print("📊 SESSION STATISTICS")
        print("="*60)
        print(f"💬 Total messages: {self.stats['messages_received']}")
        print(f"✅ Successful transcriptions: {self.stats['successful_transcriptions']}")
        print(f"❌ Failed transcriptions: {self.stats['failed_transcriptions']}")
        
        if self.stats['start_time']:
            duration = time.time() - self.stats['start_time']
            print(f"⏱️  Session duration: {int(duration)}s ({duration/60:.1f} minutes)")
            
            if self.stats['messages_received'] > 0:
                avg_time = duration / self.stats['messages_received']
                print(f"📈 Average time per message: {avg_time:.1f}s")
        
        success_rate = 0
        total_attempts = self.stats['successful_transcriptions'] + self.stats['failed_transcriptions']
        if total_attempts > 0:
            success_rate = (self.stats['successful_transcriptions'] / total_attempts) * 100
        print(f"🎯 Success rate: {success_rate:.1f}%")
        print("="*60 + "\n")
    
    async def _speak_greeting(self):
        """Speak initial greeting"""
        greeting = "Hello! I am your enhanced robot. I can now intelligently detect when you start and stop speaking! Try talking to me naturally."
        self.logger.info(f"Speaking: {greeting}")
        await self.text_to_speech.speak(greeting)
        
        # Give user a moment
        await asyncio.sleep(1)
        
        # Additional instructions
        instructions = "Say exit, quit, or goodbye when you want to stop."
        await self.text_to_speech.speak(instructions)
        await asyncio.sleep(0.5)
    
    def stop(self):
        """Stop the robot"""
        self.is_running = False
        self.conversation_active = False
        self.logger.info("🛑 Robot stopping...")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("🧹 Cleaning up robot resources...")
        
        if hasattr(self, 'text_to_speech'):
            self.text_to_speech.cleanup()
        
        if hasattr(self, 'speech_recognizer'):
            self.speech_recognizer.cleanup()
        
        self.logger.info("✅ Cleanup complete")
