"""
Status Reporter - Generate robot status information
Simple, safe status reporting for operator control
"""
import logging
from typing import Optional
from datetime import datetime, timedelta


class StatusReporter:
    """
    Generate robot status reports for operator monitoring
    """
    
    def __init__(self, robot_controller=None):
        self.logger = logging.getLogger(__name__)
        self.robot_controller = robot_controller
        self.start_time = datetime.now()
    
    def get_status(self) -> str:
        """
        Generate simple status report
        
        Returns:
            Formatted status string
        """
        try:
            lines = []
            lines.append("🤖 Robot Status:")
            lines.append("")
            
            # Basic status
            if self.robot_controller:
                if self.robot_controller.is_running:
                    lines.append("✅ Running")
                else:
                    lines.append("⏸️ Stopped")
                
                # Statistics
                stats = self.robot_controller.stats
                lines.append(f"💬 Messages: {stats.get('messages_received', 0)}")
                lines.append(f"✅ Success: {stats.get('successful_transcriptions', 0)}")
                lines.append(f"❌ Failed: {stats.get('failed_transcriptions', 0)}")
                
                if self.robot_controller.llm_enabled:
                    lines.append(f"🧠 AI: Active")
                    lines.append(f"🤖 Responses: {stats.get('llm_responses', 0)}")
                else:
                    lines.append(f"🧠 AI: Disabled")
                
                # Uptime
                if stats.get('start_time'):
                    uptime = datetime.now().timestamp() - stats['start_time']
                    uptime_str = str(timedelta(seconds=int(uptime)))
                    lines.append(f"⏱️ Uptime: {uptime_str}")
                
                # Text input stats
                if hasattr(self.robot_controller, 'text_handler'):
                    text_stats = self.robot_controller.text_handler.get_stats()
                    lines.append(f"📝 Text Input: {text_stats.get('total_received', 0)} received")
                    if text_stats.get('queue_size', 0) > 0:
                        lines.append(f"⏳ Pending: {text_stats.get('queue_size', 0)}")
            else:
                lines.append("⚠️ Controller not available")
            
            # Overall uptime
            total_uptime = datetime.now() - self.start_time
            lines.append(f"🕐 Total: {str(total_uptime).split('.')[0]}")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"❌ Error generating status: {e}")
            return f"⚠️ Status Error: {str(e)}"
    
    def get_short_status(self) -> str:
        """Get very short status (for quick replies)"""
        try:
            if not self.robot_controller:
                return "⚠️ Status unavailable"
            
            if self.robot_controller.is_running:
                messages = self.robot_controller.stats.get('messages_received', 0)
                return f"✅ Running | 💬 {messages} messages"
            else:
                return "⏸️ Stopped"
                
        except Exception as e:
            return f"⚠️ Error: {str(e)}"
