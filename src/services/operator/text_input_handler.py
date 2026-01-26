"""
Text Input Handler - Isolated text queue for operator control
Safe, isolated component that doesn't affect robot if it fails
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime


class TextInputHandler:
    """
    Thread-safe text input queue for operator control
    
    Features:
    - Isolated from robot core (safe failure)
    - Thread-safe async queue
    - Priority text input (operator override)
    - Statistics tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.queue = asyncio.Queue()
        self.stats = {
            'total_received': 0,
            'total_processed': 0,
            'last_received': None,
            'last_processed': None
        }
        self.logger.info("📝 Text Input Handler initialized")
    
    async def add_text(self, text: str, source: str = "manual") -> bool:
        """
        Add text to queue (non-blocking)
        
        Args:
            text: Text message to process
            source: Source of text ("telegram", "manual", "api", etc.)
            
        Returns:
            True if added successfully
        """
        try:
            if not text or not text.strip():
                self.logger.warning("⚠️ Empty text ignored")
                return False
            
            # Add timestamp and source metadata
            item = {
                'text': text.strip(),
                'source': source,
                'timestamp': datetime.now(),
                'id': self.stats['total_received'] + 1
            }
            
            await self.queue.put(item)
            self.stats['total_received'] += 1
            self.stats['last_received'] = datetime.now()
            
            self.logger.info(f"📥 Text queued [{source}]: {text[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add text to queue: {e}")
            return False
    
    async def get_text(self, timeout: float = 0.1) -> Optional[str]:
        """
        Get next text from queue (non-blocking with timeout)
        
        Args:
            timeout: Maximum time to wait (seconds). 0 = non-blocking
            
        Returns:
            Text string or None if queue empty/timeout
        """
        try:
            # Try to get item with timeout
            item = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            
            text = item['text']
            source = item.get('source', 'unknown')
            
            self.stats['total_processed'] += 1
            self.stats['last_processed'] = datetime.now()
            
            self.logger.info(f"📤 Text dequeued [{source}]: {text[:50]}...")
            return text
            
        except asyncio.TimeoutError:
            # Queue empty, timeout - this is normal, not an error
            return None
        except Exception as e:
            self.logger.error(f"❌ Error getting text from queue: {e}")
            return None
    
    def has_text(self) -> bool:
        """Check if queue has items (non-blocking check)"""
        return not self.queue.empty()
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def get_stats(self) -> dict:
        """Get statistics"""
        return {
            **self.stats,
            'queue_size': self.queue.qsize(),
            'pending': self.queue.qsize()
        }
    
    def clear_queue(self):
        """Clear all pending text (emergency stop)"""
        cleared = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                cleared += 1
            except:
                break
        self.logger.info(f"🧹 Cleared {cleared} items from text queue")
        return cleared
