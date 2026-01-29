"""
Telegram Bot - Isolated operator control
Safe, isolated component that doesn't affect robot if it fails
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    from telegram.error import Conflict, NetworkError, TimedOut
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("⚠️ python-telegram-bot not installed. Telegram bot disabled.")


class TelegramBot:
    """
    Isolated Telegram bot for operator control
    
    Features:
    - Receives text messages → adds to text queue
    - Sends status on request
    - Completely isolated (robot works if this fails)
    - Runs in separate async task
    """
    
    def __init__(
        self,
        token: str,
        text_handler,
        status_reporter,
        on_operator_text: Optional[callable] = None,
        mode_callback: Optional[callable] = None,
        conversation_mode_callback: Optional[callable] = None,
        speech_callback: Optional[callable] = None,
    ):
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
        
        self.token = token
        self.text_handler = text_handler
        self.status_reporter = status_reporter
        # Optional callback to interrupt mic listening immediately (operator override)
        # Must be fast + never raise (we wrap in try/except anyway)
        self.on_operator_text = on_operator_text
        # Optional callback to change input mode (voice/text/hybrid)
        self.mode_callback = mode_callback
        # Optional callback to change conversation mode (chat/speak)
        self.conversation_mode_callback = conversation_mode_callback
        # Optional callback to trigger speech scripts
        self.speech_callback = speech_callback
        
        # Import speech scripts
        from src.services.operator.speech_scripts import SpeechScripts
        self.speech_scripts = SpeechScripts()
        self.logger = logging.getLogger(__name__)
        self.application = None
        self.running = False
        self.stats = {
            'messages_received': 0,
            'status_requests': 0,
            'errors': 0,
            'start_time': None
        }
    
    async def start(self):
        """Start the Telegram bot (isolated async task)"""
        if not self.token:
            self.logger.warning("⚠️ Telegram token not provided. Telegram bot disabled.")
            return
        
        try:
            self.logger.info("🤖 Starting Telegram bot...")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("status", self._handle_status))
            self.application.add_handler(CommandHandler("mic", self._handle_mic_command))
            self.application.add_handler(CommandHandler("mode", self._handle_mode_command))
            self.application.add_handler(CommandHandler("speech", self._handle_speech_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # Start bot
            await self.application.initialize()
            await self.application.start()
            
            # Configure updater to handle conflicts gracefully
            # Use drop_pending_updates to avoid conflicts with other instances
            # Set error handlers to catch polling errors
            try:
                await self.application.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=["message", "callback_query"],
                    poll_interval=1.0,
                    timeout=10
                )
            except Conflict:
                # Conflict during polling - another instance exists
                self.logger.warning("⚠️ Telegram polling conflict - another bot instance detected")
                self.logger.info("   Robot will continue, but Telegram may not work")
                self.logger.info("   Solution: Stop other bot instances")
                raise  # Re-raise to be caught by outer handler
            
            self.running = True
            self.stats['start_time'] = datetime.now()
            self.logger.info("✅ Telegram bot started successfully")
            
        except Conflict as e:
            # Another bot instance is running - this is recoverable
            self.logger.warning(f"⚠️ Telegram bot conflict: Another instance may be running")
            self.logger.info("   Robot will continue without Telegram control")
            self.logger.info("   Solution: Stop other bot instances or wait a few seconds")
            self.stats['errors'] += 1
            self.running = False
            # Don't raise - robot should continue!
        except Exception as e:
            self.logger.error(f"❌ Failed to start Telegram bot: {e}")
            self.logger.info("   Robot will continue without Telegram control")
            self.stats['errors'] += 1
            self.running = False
            # Don't raise - robot should continue!
    
    async def stop(self):
        """Stop the Telegram bot gracefully"""
        if not self.running or not self.application:
            return
        
        try:
            self.logger.info("🛑 Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.running = False
            self.logger.info("✅ Telegram bot stopped")
        except Exception as e:
            self.logger.error(f"❌ Error stopping Telegram bot: {e}")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            welcome = (
                "🤖 **Torres Robot Control**\n\n"
                "Welcome! I'm your robot operator interface.\n\n"
                "**Quick Commands:**\n"
                "`/help` - Show all commands\n"
                "`/status` - Check robot status\n"
                "`/mic` - Control input mode\n\n"
                "Send any message to forward to robot.\n\n"
                "✅ Bot is active!"
            )
            await update.message.reply_text(welcome, parse_mode='Markdown')
        except Exception as e:
            self.logger.error(f"❌ Error handling /start: {e}")
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            # Get current mode if available
            current_mode = "unknown"
            mode_icon = "🎤📝"
            conv_mode = "chat"
            conv_icon = "🤖"
            if hasattr(self.status_reporter, 'robot_controller') and self.status_reporter.robot_controller:
                rc = self.status_reporter.robot_controller
                current_mode = rc.get_input_mode()
                mode_icons = {"voice": "🎤", "text": "📝", "hybrid": "🎤📝"}
                mode_icon = mode_icons.get(current_mode, "🎤📝")
                if hasattr(rc, "get_conversation_mode"):
                    conv_mode = rc.get_conversation_mode()
                conv_icons = {"chat": "🤖", "speak": "🗣️"}
                conv_icon = conv_icons.get(conv_mode, "🤖")
            
            help_text = (
                "📖 **Torres Robot Control - Help**\n\n"
                "**Available Commands:**\n\n"
                "`/start` - Welcome message\n"
                "`/help` - Show this help\n"
                "`/status` - Detailed robot status\n\n"
                "**Mode Control:**\n"
                "`/mic off` - 📝 TEXT ONLY (disable mic)\n"
                "`/mic on` - 🎤 VOICE ONLY (enable mic)\n"
                "`/mic hybrid` - 🎤📝 BOTH (text priority)\n\n"
                "**Conversation Mode:**\n"
                "`/mode chat` - 🤖 Chat with AI (default)\n"
                "`/mode speak` - 🗣️ Direct speak (no AI, speak text)\n\n"
                f"**Current Input Mode:** {mode_icon} {current_mode.upper()}\n"
                f"**Current Conversation Mode:** {conv_icon} {conv_mode.upper()}\n\n"
                "**Usage:**\n"
                "• Send any text message → Robot processes it\n"
                "• Use `/mic off` if mic breaks → Text only mode\n"
                "• Use `/status` to monitor robot health\n\n"
                "💡 **Tip:** In text mode, robot responds instantly with no mic lag!"
            )
            await update.message.reply_text(help_text, parse_mode='Markdown')
        except Exception as e:
            self.logger.error(f"❌ Error handling /help: {e}")
            await update.message.reply_text("⚠️ Error showing help")
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            self.stats['status_requests'] += 1
            status = self.status_reporter.get_status()
            
            # Add current modes to status if available
            if hasattr(self.status_reporter, 'robot_controller') and self.status_reporter.robot_controller:
                rc = self.status_reporter.robot_controller
                current_mode = rc.get_input_mode()
                mode_icons = {"voice": "🎤", "text": "📝", "hybrid": "🎤📝"}
                mode_icon = mode_icons.get(current_mode, "🎤📝")
                
                conv_mode = getattr(rc, "get_conversation_mode", lambda: "chat")()
                conv_icons = {"chat": "🤖", "speak": "🗣️"}
                conv_icon = conv_icons.get(conv_mode, "🤖")
                
                status = (
                    f"{status}\n\n"
                    f"**Input Mode:** {mode_icon} {current_mode.upper()}\n"
                    f"**Conversation Mode:** {conv_icon} {conv_mode.upper()}"
                )
            
            await update.message.reply_text(status, parse_mode='Markdown')
        except Exception as e:
            self.logger.error(f"❌ Error handling /status: {e}")
            await update.message.reply_text(f"⚠️ Error getting status: {str(e)}")
    
    async def _handle_mic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mic command - Mode switching"""
        try:
            if not context.args or len(context.args) == 0:
                # Show current mode and help
                current_mode = "unknown"
                if hasattr(self.status_reporter, 'robot_controller') and self.status_reporter.robot_controller:
                    current_mode = self.status_reporter.robot_controller.get_input_mode()
                
                mode_icons = {"voice": "🎤", "text": "📝", "hybrid": "🎤📝"}
                mode_icon = mode_icons.get(current_mode, "🎤📝")
                
                help_text = (
                    "🎤 **Mic Control Commands:**\n\n"
                    "`/mic off` - Disable mic, TEXT ONLY mode\n"
                    "`/mic on` - Enable mic, VOICE ONLY mode\n"
                    "`/mic hybrid` - Both mic + text (text priority)\n\n"
                    f"**Current Mode:** {mode_icon} {current_mode.upper()}\n\n"
                    "💡 Use `/status` for full robot status"
                )
                await update.message.reply_text(help_text, parse_mode='Markdown')
                return
            
            command = context.args[0].lower()
            
            if not self.mode_callback:
                await update.message.reply_text("⚠️ Mode switching not available")
                return
            
            # Map commands to modes
            mode_map = {
                "off": "text",
                "on": "voice",
                "hybrid": "hybrid"
            }
            
            if command not in mode_map:
                await update.message.reply_text(f"⚠️ Invalid command. Use: `/mic off`, `/mic on`, or `/mic hybrid`", parse_mode='Markdown')
                return
            
            new_mode = mode_map[command]
            success = self.mode_callback(new_mode)
            
            if success:
                mode_icons = {
                    "voice": "🎤",
                    "text": "📝",
                    "hybrid": "🎤📝"
                }
                icon = mode_icons.get(new_mode, "🎤")
                await update.message.reply_text(f"{icon} **Mode changed to: {new_mode.upper()}**\n\nRobot will now {'only listen to mic' if new_mode == 'voice' else 'only process text' if new_mode == 'text' else 'listen to both (text priority)'}.", parse_mode='Markdown')
            else:
                await update.message.reply_text("⚠️ Failed to change mode")
                
        except Exception as e:
            self.logger.error(f"❌ Error handling /mic command: {e}")
            await update.message.reply_text(f"⚠️ Error: {str(e)}")

    async def _handle_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mode command - Conversation mode switching (chat/speak)"""
        try:
            if not context.args or len(context.args) == 0:
                # Show current conversation mode and help
                conv_mode = "chat"
                if hasattr(self.status_reporter, 'robot_controller') and self.status_reporter.robot_controller:
                    conv_mode = self.status_reporter.robot_controller.get_conversation_mode()
                conv_icons = {"chat": "🤖", "speak": "🗣️"}
                conv_icon = conv_icons.get(conv_mode, "🤖")
                
                help_text = (
                    "🧠 **Conversation Mode Commands:**\n\n"
                    "`/mode chat`  - 🤖 Use AI (normal conversation)\n"
                    "`/mode speak` - 🗣️ Direct speak (no AI, speak text)\n\n"
                    f"**Current Conversation Mode:** {conv_icon} {conv_mode.upper()}\n\n"
                    "💡 Use `speak` mode for exhibition scripts: robot will speak exactly what you type."
                )
                await update.message.reply_text(help_text, parse_mode='Markdown')
                return
            
            if not self.conversation_mode_callback:
                await update.message.reply_text("⚠️ Conversation mode switching not available")
                return
            
            command = context.args[0].lower()
            mode_map = {
                "chat": "chat",
                "speak": "speak",
                "direct": "speak",
            }
            
            if command not in mode_map:
                await update.message.reply_text(
                    "⚠️ Invalid command. Use: `/mode chat` or `/mode speak`",
                    parse_mode='Markdown'
                )
                return
            
            new_mode = mode_map[command]
            success = self.conversation_mode_callback(new_mode)
            
            if success:
                conv_icons = {"chat": "🤖", "speak": "🗣️"}
                conv_icon = conv_icons.get(new_mode, "🤖")
                if new_mode == "chat":
                    detail = "Robot will answer using AI (LLM)."
                else:
                    detail = "Robot will speak your text directly (no AI)."
                await update.message.reply_text(
                    f"{conv_icon} **Conversation mode changed to: {new_mode.upper()}**\n\n{detail}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("⚠️ Failed to change conversation mode")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling /mode command: {e}")
            await update.message.reply_text(f"⚠️ Error: {str(e)}")
    
    async def _handle_speech_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /speech command - Trigger pre-written speeches"""
        try:
            if not context.args or len(context.args) == 0:
                # Show available speeches
                speeches = self.speech_scripts.list_speeches()
                
                if not speeches:
                    await update.message.reply_text("⚠️ No speeches available")
                    return
                
                speech_list = "🎤 **Available Speeches:**\n\n"
                for speech_id, info in speeches.items():
                    speech_list += f"`/speech {speech_id}` - {info['title']}\n"
                
                speech_list += "\n💡 Use `/speech <name>` to trigger a speech"
                await update.message.reply_text(speech_list, parse_mode='Markdown')
                return
            
            speech_id = context.args[0].lower()
            speech = self.speech_scripts.get_speech(speech_id)
            
            if not speech:
                await update.message.reply_text(
                    f"⚠️ Speech '{speech_id}' not found. Use `/speech` to see available speeches.",
                    parse_mode='Markdown'
                )
                return
            
            # Trigger the speech via callback
            if self.speech_callback:
                try:
                    await self.speech_callback(speech["content"])
                    await update.message.reply_text(
                        f"🎤 **Speech triggered:** {speech['title']}\n\n"
                        f"Torres is now speaking...",
                        parse_mode='Markdown'
                    )
                except Exception as cb_err:
                    self.logger.error(f"❌ Speech callback error: {cb_err}")
                    await update.message.reply_text(f"⚠️ Failed to trigger speech: {str(cb_err)}")
            else:
                await update.message.reply_text("⚠️ Speech feature not available (callback not set)")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling /speech command: {e}")
            await update.message.reply_text(f"⚠️ Error: {str(e)}")

    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        try:
            text = update.message.text
            chat_id = update.message.chat.id
            
            self.logger.info(f"📨 Telegram message received: {text[:50]}...")
            self.stats['messages_received'] += 1

            # Operator override: interrupt mic listening immediately so text is processed ASAP
            if self.on_operator_text:
                try:
                    self.on_operator_text()
                except Exception as cb_err:
                    self.logger.debug(f"Operator interrupt callback failed: {cb_err}")
            
            # Add to text queue (for robot to process)
            success = await self.text_handler.add_text(text, source="telegram")
            
            if success:
                # Send acknowledgment with status
                status = self.status_reporter.get_short_status()
                reply = f"✅ Message received!\n\n{status}"
                await update.message.reply_text(reply)
            else:
                await update.message.reply_text("⚠️ Failed to queue message. Robot may be busy.")
                
        except Exception as e:
            self.logger.error(f"❌ Error handling Telegram message: {e}")
            self.stats['errors'] += 1
            try:
                await update.message.reply_text(f"⚠️ Error: {str(e)}")
            except:
                pass  # If we can't reply, that's okay - robot continues
    
    def get_stats(self) -> dict:
        """Get bot statistics"""
        return {
            **self.stats,
            'running': self.running,
            'uptime': str(datetime.now() - self.stats['start_time']) if self.stats['start_time'] else None
        }
