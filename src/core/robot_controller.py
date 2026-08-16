import asyncio
import logging
import time
import signal
from typing import Optional
from src.services.tts.tts_service import TTSService
from src.services.speech.speech_recognizer import SpeechRecognizer
from src.services.llm.llm_service import LLMService
from src.core.state import NilaState
from src.core.runtime import NilaRuntime

class RobotController:
    """Enhanced Robot Controller - Step 4: Speaking + Listening + AI + Multilingual TTS"""
    
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
        
        # Step 3: Initialize LLM service
        try:
            self.llm_service = LLMService(settings)
            self.llm_enabled = True
            self.logger.info("🧠 LLM Service enabled - AI responses active!")
        except Exception as e:
            self.logger.warning(f"⚠️ LLM Service initialization failed: {e}")
            self.logger.info("   Robot will run without AI responses (echo mode)")
            self.llm_service = None
            self.llm_enabled = False
            
        # Initialize Feedback Service
        from src.services.feedback.feedback_service import FeedbackService
        self.feedback = FeedbackService(settings)

        # Initialize Wake Word Detector
        from src.services.speech.wake_word_detector import WakeWordDetector
        self.wake_detector = WakeWordDetector(settings)

        # Initialize NilaRuntime Manager
        self.runtime = NilaRuntime(settings)
        self.event_bus = self.runtime.event_bus
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        mode = "AI Conversations" if self.llm_enabled else "Echo Mode"
        self.logger.info(f"🤖 Enhanced Robot Controller initialized - {mode}")

    def _setup_signal_handlers(self):
        """Setup graceful shutdown on CTRL+C"""
        def signal_handler(signum, frame):
            self.logger.info("⏸️ Shutdown signal received...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the robot - Step 3: Speak greeting, listen, and respond with AI"""
        self.is_running = True
        self.conversation_active = True
        self.stats['start_time'] = time.time()
        
        # Set active loop on EventBus
        self.event_bus.set_event_loop(asyncio.get_running_loop())
        self.runtime.start_new_session()
        
        self.logger.info("🚀 Robot starting Event-Driven Runtime Loop...")
        
        # Step 3: Speak greeting
        await self._speak_greeting()
        
        # Step 3: AI conversation loop
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while self.is_running and self.conversation_active:
            try:
                self._print_status_header()
                self.runtime.start_turn()
                
                # Transition to LISTENING state
                self.runtime.transition_to(NilaState.LISTENING, reason="Awaiting user voice input")
                
                # Listen for voice input
                user_input = await self.speech_recognizer.listen(timeout=30)
                
                if user_input:
                    consecutive_failures = 0  # Reset failure counter
                    self.stats['messages_received'] += 1
                    self.stats['successful_transcriptions'] += 1
                    
                    # Publish STTTranscriptEvent
                    from src.core.events import STTTranscriptEvent
                    await self.event_bus.publish(STTTranscriptEvent(
                        text=user_input,
                        language=self.speech_recognizer.get_last_language(),
                        confidence=1.0
                    ))
                    
                    # Display recorded message with analysis
                    self._display_message_info(user_input)
                    
                    # Check for exit commands
                    if self._is_exit_command(user_input):
                        await self._handle_exit()
                        break
                    
                    # Step 3: Get AI response and show it
                    await self._handle_conversation(user_input)
                    
                else:
                    self.stats['failed_transcriptions'] += 1
                    consecutive_failures += 1
                    self.runtime.transition_to(NilaState.IDLE, reason="No speech detected")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"\n⚠️ {consecutive_failures} consecutive failures. Check microphone!")
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
        self.logger.info("✅ Step 3 complete!")
    
    async def _handle_conversation(self, user_input: str):
        """Handle conversation - Get AI response and display"""
        if not self.llm_enabled or self.llm_service is None:
            # Echo mode fallback
            print(f"\n🤖 ROBOT (Echo Mode): You said '{user_input}'")
            return
        
        try:
            print(f"\n🧠 Generating AI response...")
            language = self.speech_recognizer.get_last_language()
            
            # Publish thinking start event (FeedbackService automatically handles audio loop)
            from src.core.events import BrainThinkingEvent, BrainLLMResponseEvent, TTSPlaybackEvent
            await self.event_bus.publish(BrainThinkingEvent(is_thinking=True))
            
            try:
                ai_response = await self.llm_service.get_response(user_input, language)
            finally:
                # Publish thinking stop event
                await self.event_bus.publish(BrainThinkingEvent(is_thinking=False))
            
            if ai_response:
                self.stats['llm_responses'] += 1
                
                # Publish LLM response event
                await self.event_bus.publish(BrainLLMResponseEvent(text=ai_response))
                
                # Display AI response
                print("\n" + "="*60)
                print("🤖 ROBOT RESPONSE:")
                print("="*60)
                print(f"{ai_response}")
                print("="*60)
                
                # Speak the AI response!
                print("\n🔊 Speaking response...")
                await self.event_bus.publish(TTSPlaybackEvent(status="started"))
                await self.text_to_speech.speak(ai_response)
                await self.event_bus.publish(TTSPlaybackEvent(status="finished"))
                
            else:
                self.stats['llm_failures'] += 1
                print("❌ Failed to generate response")
                
        except Exception as e:
            self.stats['llm_failures'] += 1
            self.logger.error(f"❌ Conversation error: {e}")
            print(f"❌ Error: {e}")
    
    def _print_status_header(self):
        """Print status header for each listening cycle"""
        print("\n" + "="*60)
        print("🎯 ROBOT LISTENING MODE" + (" - AI ACTIVE 🧠" if self.llm_enabled else " - ECHO MODE"))
        print("="*60)
        print(f"💬 Messages received: {self.stats['messages_received']}")
        print(f"✅ Successful: {self.stats['successful_transcriptions']} | ❌ Failed: {self.stats['failed_transcriptions']}")
        if self.llm_enabled:
            print(f"🧠 AI Responses: {self.stats['llm_responses']} | ❌ AI Failures: {self.stats['llm_failures']}")
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
    
    def _print_final_stats(self):
        """Print final statistics before shutdown"""
        print("\n" + "="*60)
        print("📊 SESSION STATISTICS")
        print("="*60)
        print(f"💬 Total messages: {self.stats['messages_received']}")
        print(f"✅ Successful transcriptions: {self.stats['successful_transcriptions']}")
        print(f"❌ Failed transcriptions: {self.stats['failed_transcriptions']}")
        
        if self.llm_enabled:
            print(f"🧠 AI Responses: {self.stats['llm_responses']}")
            print(f"❌ AI Failures: {self.stats['llm_failures']}")
            
            # Show LLM stats
            if self.llm_service:
                llm_stats = self.llm_service.get_stats()
                print(f"📊 Total tokens used: {llm_stats.get('total_tokens_used', 0)}")
                print(f"💰 Estimated cost: ${llm_stats.get('estimated_cost', 0):.4f}")
        
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
        greeting = "Hey welcome, I'm Nila."
        
        self.logger.info(f"Speaking: {greeting}")
        await self.text_to_speech.speak(greeting)
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
        
        if hasattr(self, 'llm_service') and self.llm_service:
            self.llm_service.cleanup()
            
        if hasattr(self, 'feedback'):
            self.feedback.cleanup()
        
        self.logger.info("✅ Cleanup complete")
