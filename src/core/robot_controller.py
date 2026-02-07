import asyncio
import logging
import time
import signal
from typing import Optional
from src.services.tts.tts_service import TTSService
from src.services.speech.speech_recognizer import SpeechRecognizer
from src.services.llm.llm_service import LLMService
from src.services.chat.basic_response_handler import BasicResponseHandler

class RobotController:
    """Enhanced Robot Controller - Step 4: Speaking + Listening + AI + Multilingual TTS"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.conversation_active = False
        
        # Input mode: "voice", "text", or "hybrid" (default: both, text priority)
        self.input_mode = "hybrid"  # Can be changed via Telegram commands
        
        # Conversation mode: "chat" (LLM) or "speak" (direct TTS of input text)
        # "chat" = normal AI conversation
        # "speak" = bypass LLM, speak exactly what operator sends
        self.conversation_mode = "chat"
        
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
        
        # Initialize Basic Response Handler
        self.basic_responses = BasicResponseHandler()
        
        # Initialize Operator Control (Text Input Handler)
        from src.services.operator.text_input_handler import TextInputHandler
        from src.services.operator.status_reporter import StatusReporter
        self.text_handler = TextInputHandler()
        self.status_reporter = StatusReporter(robot_controller=self)
        self.telegram_bot = None
        
        # Initialize Telegram Bot (optional, isolated)
        if getattr(settings, 'TELEGRAM_ENABLED', False) and getattr(settings, 'TELEGRAM_BOT_TOKEN', ''):
            try:
                from src.services.operator.telegram_bot import TelegramBot
                self.telegram_bot = TelegramBot(
                    token=settings.TELEGRAM_BOT_TOKEN,
                    text_handler=self.text_handler,
                    status_reporter=self.status_reporter,
                    on_operator_text=self.interrupt_listening,
                    mode_callback=self.set_input_mode,              # Input mode (mic/text/hybrid)
                    conversation_mode_callback=self.set_conversation_mode,  # Conversation mode (chat/speak)
                    speech_callback=self.trigger_speech             # Speech script trigger
                )
                self.logger.info("📱 Telegram bot initialized (will start when robot starts)")
            except Exception as e:
                self.logger.warning(f"⚠️ Telegram bot initialization failed: {e}")
                self.logger.info("   Robot will continue without Telegram control")
                self.telegram_bot = None
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        mode = "AI Conversations" if self.llm_enabled else "Echo Mode"
        telegram_status = " + Telegram" if self.telegram_bot else ""
        self.logger.info(f"🤖 Enhanced Robot Controller initialized - {mode}{telegram_status}")

    def interrupt_listening(self):
        """
        Operator override: interrupt current mic listening ASAP.
        Safe to call anytime (even if not currently listening).
        """
        try:
            if hasattr(self, 'speech_recognizer') and hasattr(self.speech_recognizer, 'audio_capture'):
                self.speech_recognizer.audio_capture.request_stop()
                self.logger.info("🛑 Operator override: interrupted mic listening")
        except Exception as e:
            self.logger.debug(f"Operator interrupt failed: {e}")
    
    def set_input_mode(self, mode: str):
        """
        Set input mode: "voice", "text", or "hybrid"
        
        Args:
            mode: "voice" = only mic, "text" = only Telegram/text, "hybrid" = both (text priority)
        """
        valid_modes = ["voice", "text", "hybrid"]
        if mode.lower() not in valid_modes:
            self.logger.warning(f"⚠️ Invalid mode: {mode}. Valid: {valid_modes}")
            return False
        
        old_mode = self.input_mode
        self.input_mode = mode.lower()
        
        # Log mode change with clear indication
        mode_descriptions = {
            "voice": "🎤 VOICE ONLY (mic active, text disabled)",
            "text": "📝 TEXT ONLY (mic disabled, Telegram/text only)",
            "hybrid": "🎤📝 HYBRID (both active, text priority)"
        }
        desc = mode_descriptions.get(self.input_mode, self.input_mode)
        self.logger.info(f"🔄 Input mode changed: {old_mode.upper()} → {self.input_mode.upper()}")
        self.logger.info(f"   {desc}")
        print(f"\n{'='*60}")
        print(f"🔄 MODE CHANGE: {old_mode.upper()} → {self.input_mode.upper()}")
        print(f"   {desc}")
        print(f"{'='*60}\n")
        
        # If switching to text-only, stop any current mic listening
        if self.input_mode == "text":
            self.interrupt_listening()
            print("📝 Mic disabled - Robot will only process text input")
        elif self.input_mode == "voice":
            print("🎤 Mic enabled - Robot will only listen to voice")
        else:
            print("🎤📝 Hybrid mode - Text has priority, mic also active")
        
        return True
    
    def get_input_mode(self) -> str:
        """Get current input mode"""
        return self.input_mode
    
    def set_conversation_mode(self, mode: str) -> bool:
        """
        Set conversation mode:
        - "chat"  = normal LLM conversation
        - "speak" = direct TTS (speak the exact text, no LLM)
        """
        valid_modes = ["chat", "speak"]
        if mode.lower() not in valid_modes:
            self.logger.warning(f"⚠️ Invalid conversation mode: {mode}. Valid: {valid_modes}")
            return False
        
        old_mode = self.conversation_mode
        self.conversation_mode = mode.lower()
        
        desc = {
            "chat": "🤖 CHAT MODE (LLM responses)",
            "speak": "🗣️ DIRECT SPEAK MODE (no LLM, speak operator text)"
        }.get(self.conversation_mode, self.conversation_mode)
        
        self.logger.info(f"🔄 Conversation mode changed: {old_mode.upper()} → {self.conversation_mode.upper()}")
        self.logger.info(f"   {desc}")
        print(f"\n{'='*60}")
        print(f"🔄 CONVERSATION MODE: {old_mode.upper()} → {self.conversation_mode.upper()}")
        print(f"   {desc}")
        print(f"{'='*60}\n")
        return True
    
    def get_conversation_mode(self) -> str:
        """Get current conversation mode"""
        return self.conversation_mode
    
    async def trigger_speech(self, speech_text: str):
        """
        Trigger a pre-written speech (bypasses LLM, direct TTS)
        Used for exhibition speeches and scripted content
        """
        try:
            self.logger.info(f"🎤 Triggering speech script ({len(speech_text)} chars)")
            
            # Interrupt any current listening
            self.interrupt_listening()
            
            # Speak the entire speech directly (no LLM)
            await self.text_to_speech.speak(speech_text)
            
            # Wait for speech to complete
            await self.text_to_speech.wait_until_done()
            
            self.logger.info("✅ Speech script completed")
            
        except Exception as e:
            self.logger.error(f"❌ Speech trigger error: {e}")
            raise
    
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
        
        self.logger.info("🚀 Robot starting Step 3...")
        
        # Start TTS Service (Background Worker)
        await self.text_to_speech.start()
        
        # Start Telegram Bot (if enabled, isolated)
        if self.telegram_bot:
            try:
                await self.telegram_bot.start()
                self.logger.info("✅ Telegram bot started")
            except Exception as e:
                self.logger.error(f"❌ Telegram bot failed to start: {e}")
                self.logger.info("   Robot will continue without Telegram")
                self.telegram_bot = None
        
        # Step 3: Speak greeting
        await self._speak_greeting()
        
        # Step 3: AI conversation loop
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while self.is_running and self.conversation_active:
            try:
                self._print_status_header()
                
                # MODE-BASED INPUT HANDLING
                user_input = None
                
                # TEXT MODE: Only check text queue (mic disabled)
                if self.input_mode == "text":
                    try:
                        user_input = await self.text_handler.get_text(timeout=1.0)  # Wait a bit for text
                        if user_input:
                            self.logger.info(f"📝 Processing text input: {user_input[:50]}...")
                            self.stats['messages_received'] += 1
                            self._display_message_info(user_input, source="text")
                    except Exception as text_err:
                        self.logger.debug(f"Text queue check: {text_err}")
                
                # VOICE MODE: Only listen to mic (text disabled)
                elif self.input_mode == "voice":
                    try:
                        user_input = await self.speech_recognizer.listen_streaming(timeout=30)
                    except Exception as stream_err:
                        self.logger.warning(f"⚠️ Streaming failed: {stream_err}, using batch mode")
                        user_input = await self.speech_recognizer.listen(timeout=30)
                    
                    if user_input:
                        self.stats['successful_transcriptions'] += 1
                        self._display_message_info(user_input, source="voice")
                
                # HYBRID MODE: Text first, then voice (default)
                else:  # hybrid
                    # PRIORITY 1: Check text queue first (operator override - TEXT FIRST)
                    try:
                        user_input = await self.text_handler.get_text(timeout=0.1)  # Non-blocking check
                        if user_input:
                            self.logger.info(f"📝 Processing text input: {user_input[:50]}...")
                            self.stats['messages_received'] += 1
                            self._display_message_info(user_input, source="text")
                    except Exception as text_err:
                        self.logger.debug(f"Text queue check: {text_err}")
                    
                    # PRIORITY 2: Voice input (if no text available)
                    if not user_input:
                        try:
                            user_input = await self.speech_recognizer.listen_streaming(timeout=30)
                        except Exception as stream_err:
                            self.logger.warning(f"⚠️ Streaming failed: {stream_err}, using batch mode")
                            user_input = await self.speech_recognizer.listen(timeout=30)
                        
                        if user_input:
                            self.stats['successful_transcriptions'] += 1
                            self._display_message_info(user_input, source="voice")
                
                if user_input:
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Check for exit commands
                    if self._is_exit_command(user_input):
                        await self._handle_exit()
                        break
                    
                    # Step 3: Get AI response and show it (no TTS yet)
                    await self._handle_conversation(user_input)
                    
                else:
                    self.stats['failed_transcriptions'] += 1
                    consecutive_failures += 1
                    
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
        """
        Handle conversation - SIMPLE MODE
        Get full AI response, then speak it all at once
        """
        # DIRECT SPEAK MODE: Bypass LLM and speak operator text directly
        if getattr(self, "conversation_mode", "chat") == "speak":
            try:
                print("\n" + "="*60)
                print("🗣️ DIRECT SPEAK MODE (No LLM):")
                print("="*60)
                print(user_input)
                print("="*60)
                
                # Direct TTS of operator text
                await self.text_to_speech.speak(user_input)
                print("⏳ Waiting for speech to finish...")
                await self.text_to_speech.wait_until_done()
            except Exception as e:
                self.logger.error(f"❌ Direct speak error: {e}")
                print(f"\n❌ Direct speak error: {e}")
            finally:
                # Ensure thinking feedback is stopped if it was started elsewhere
                try:
                    self.feedback.stop_thinking()
                except Exception:
                    pass
            return
        
        # CHAT MODE (LLM conversation)
        if not self.llm_enabled or self.llm_service is None:
            # Echo mode fallback
            print(f"\n🤖 ROBOT (Echo Mode): You said '{user_input}'")
            return
            
        # ⚡ CHECK BASIC RESPONSES FIRST (Bypass LLM)
        basic_reply = self.basic_responses.get_response(user_input)
        if basic_reply:
            print("\n" + "="*60)
            print("⚡ BASIC RESPONSE (Instant):")
            print("="*60)
            print(basic_reply)
            print("="*60)
            
            self.stats['llm_responses'] += 1 # Count as response
            
            # Speak immediately
            await self.text_to_speech.speak(basic_reply)
            print("⏳ Waiting for speech to finish...")
            await self.text_to_speech.wait_until_done()
            return
        
        try:
            print(f"\n🧠 Thinking...", end="", flush=True)
            self.feedback.start_thinking()
            
            # Get full AI response (non-streaming)
            from src.utils.latency import tracker
            tracker.track("llm_request_start")
            
            ai_response = await self.llm_service.get_response(user_input)
            
            tracker.track("llm_response_complete")
            self.feedback.stop_thinking()
            
            if ai_response:
                print("\n" + "="*60)
                print("🤖 ROBOT RESPONSE:")
                print("="*60)
                print(ai_response)
                print("="*60)
                
                self.stats['llm_responses'] += 1
                
                # Speak the full response at once
                await self.text_to_speech.speak(ai_response)
                
                # Wait for speech to finish before listening again
                # This prevents self-listening (hearing own voice)
                print("⏳ Waiting for speech to finish...")
                await self.text_to_speech.wait_until_done()
            else:
                print("\n⚠️ No response from AI")
                self.stats['llm_failures'] += 1
                
        except Exception as e:
            self.stats['llm_failures'] += 1
            self.logger.error(f"❌ Conversation error: {e}")
            print(f"\n❌ Error: {e}")
        finally:
            self.feedback.stop_thinking()
    
    def _print_status_header(self):
        """Print status header for each listening cycle"""
        from src.utils.latency import tracker
        print(tracker.get_report())
        
        mode_icon = {
            "voice": "🎤",
            "text": "📝",
            "hybrid": "🎤📝"
        }.get(self.input_mode, "🎤📝")
        
        print("\n" + "="*60)
        print(f"🎯 ROBOT LISTENING MODE [{mode_icon} {self.input_mode.upper()}]" + (" - AI ACTIVE 🧠" if self.llm_enabled else " - ECHO MODE"))
        print("="*60)
        print(f"💬 Messages received: {self.stats['messages_received']}")
        print(f"✅ Successful: {self.stats['successful_transcriptions']} | ❌ Failed: {self.stats['failed_transcriptions']}")
        if self.llm_enabled:
            print(f"🧠 AI Responses: {self.stats['llm_responses']} | ❌ AI Failures: {self.stats['llm_failures']}")
        if self.stats['start_time']:
            uptime = time.time() - self.stats['start_time']
            print(f"⏱️  Uptime: {int(uptime)}s")
        print("-" * 60)
    
    def _display_message_info(self, text: str, source: str = "voice"):
        """Display detailed information about the received message"""
        icon = "📝" if source == "text" else "🎤"
        source_label = "TEXT INPUT" if source == "text" else "VOICE INPUT"
        print(f"\n{icon} RECEIVED MESSAGE ({source_label}):")
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
        greeting = "ഹായ്, ഞാൻ ടോറസ്.റോബുവേഴ്സിൽ നിന്നാണ് ഞാൻ വന്നത്.റോബുവേഴ്സിൽ നിന്നാണ് ഞാൻ വന്നത്.റോബുവേഴ്സിൽ നിന്നാണ് ഞാൻ വന്നത്.റോബുവേഴ്സിൽ നിന്നാണ് ഞാൻ വന്നത്."
        
        self.logger.info(f"Speaking: {greeting}")
        await self.text_to_speech.speak(greeting)
        # Wait for greeting to finish playing before starting to listen
        # This prevents self-listening (hearing own voice through mic)
        await self.text_to_speech.wait_until_done()
    
    def stop(self):
        """Stop the robot"""
        self.is_running = False
        self.conversation_active = False
        self.logger.info("🛑 Robot stopping...")
        
        # Stop TTS immediately (clears queue and cancels worker)
        if hasattr(self, 'text_to_speech'):
            self.text_to_speech.stop_speaking()
        
        # Force stop audio capture to break the listening loop immediately
        if hasattr(self, 'speech_recognizer') and hasattr(self.speech_recognizer, 'audio_capture'):
            self.speech_recognizer.audio_capture.request_stop()
    
    async def cleanup_async(self):
        """Async cleanup resources (for Telegram bot)"""
        self.logger.info("🧹 Cleaning up robot resources (async)...")
        
        # Stop Telegram bot
        if self.telegram_bot:
            try:
                await self.telegram_bot.stop()
            except Exception as e:
                self.logger.error(f"❌ Error stopping Telegram bot: {e}")
        
        if hasattr(self, 'text_to_speech'):
            self.text_to_speech.cleanup()
        
        if hasattr(self, 'speech_recognizer'):
            self.speech_recognizer.cleanup()
        
        if hasattr(self, 'llm_service') and self.llm_service:
            self.llm_service.cleanup()
            
        if hasattr(self, 'feedback'):
            self.feedback.cleanup()
        
        self.logger.info("✅ Cleanup complete")
    
    def cleanup(self):
        """Cleanup resources (sync wrapper)"""
        # For sync cleanup, Telegram bot will stop when event loop closes
        # This is safe because Telegram bot runs in its own task
        self.logger.info("🧹 Cleaning up robot resources...")
        
        if hasattr(self, 'text_to_speech'):
            self.text_to_speech.cleanup()
        
        if hasattr(self, 'speech_recognizer'):
            self.speech_recognizer.cleanup()
        
        if hasattr(self, 'llm_service') and self.llm_service:
            self.llm_service.cleanup()
            
        if hasattr(self, 'feedback'):
            self.feedback.cleanup()
        
        # Note: Telegram bot cleanup happens in async context
        # It will stop automatically when event loop closes
        if self.telegram_bot:
            self.logger.info("📱 Telegram bot will stop with event loop")
        
        self.logger.info("✅ Cleanup complete")
