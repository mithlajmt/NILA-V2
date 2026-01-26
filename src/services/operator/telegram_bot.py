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
    
    def __init__(self, token: str, text_handler, status_reporter, on_operator_text: Optional[callable] = None, mode_callback: Optional[callable] = None):
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
            self.application.add_handler(CommandHandler("status", self._handle_status))
            self.application.add_handler(CommandHandler("mic", self._handle_mic_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # Start bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.running = True
            self.stats['start_time'] = datetime.now()
            self.logger.info("✅ Telegram bot started successfully")
            
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
                "🤖 **NILA Robot Control**\n\n"
                "**Commands:**\n"
                "`/status` - Check robot status\n"
                "`/mic off` - Disable mic (text only)\n"
                "`/mic on` - Enable mic (voice only)\n"
                "`/mic hybrid` - Both (text priority)\n\n"
                "Send any message to forward to robot.\n\n"
                "✅ Bot is active!"
            )
            await update.message.reply_text(welcome)
        except Exception as e:
            self.logger.error(f"❌ Error handling /start: {e}")
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            self.stats['status_requests'] += 1
            status = self.status_reporter.get_status()
            await update.message.reply_text(status)
        except Exception as e:
            self.logger.error(f"❌ Error handling /status: {e}")
            await update.message.reply_text(f"⚠️ Error getting status: {str(e)}")
    
    async def _handle_mic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mic command - Mode switching"""
        try:
            if not context.args or len(context.args) == 0:
                # Show current mode and help
                help_text = (
                    "🎤 **Mic Control Commands:**\n\n"
                    "`/mic off` - Disable mic, TEXT ONLY mode\n"
                    "`/mic on` - Enable mic, VOICE ONLY mode\n"
                    "`/mic hybrid` - Both mic + text (text priority)\n\n"
                    "**Current mode:** Check /status"
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
