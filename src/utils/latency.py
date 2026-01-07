import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class TimingEvent:
    name: str
    timestamp: float
    description: str = ""

class LatencyTracker:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LatencyTracker, cls).__new__(cls)
            cls._instance.events = []
            cls._instance.start_time = 0
            cls._instance.logger = logging.getLogger(__name__)
        return cls._instance

    def reset(self):
        """Reset the tracker for a new turn"""
        self.events = []
        self.start_time = time.perf_counter()
        # Add initial start event
        self.track("turn_start", "Start of conversation turn")

    def track(self, name: str, description: str = ""):
        """Record an event with the current timestamp"""
        if not self.events and name != "turn_start":
            self.reset()
            
        timestamp = time.perf_counter()
        self.events.append(TimingEvent(name, timestamp, description))
        # self.logger.debug(f"⏱️ EVENT: {name} ({description})")

    def get_report(self) -> str:
        """Generate a readable report of latency breakdown"""
        if not self.events:
            return "No events tracked."

        report = ["\n📊 LATENCY BREAKDOWN (Time since start)"]
        report.append("=" * 60)
        
        base_time = self.events[0].timestamp
        prev_time = base_time
        
        for i, event in enumerate(self.events):
            total_elapsed = event.timestamp - base_time
            step_elapsed = event.timestamp - prev_time
            
            # Format nicely
            icon = "🔷"
            if "stt" in event.name.lower(): icon = "🎤"
            elif "llm" in event.name.lower(): icon = "🧠"
            elif "tts" in event.name.lower(): icon = "🔈"
            elif "audio" in event.name.lower(): icon = "🔊"
            
            report.append(
                f"{icon} {event.name:<25} | +{step_elapsed:.3f}s | Total: {total_elapsed:.3f}s | {event.description}"
            )
            prev_time = event.timestamp

        report.append("=" * 60)
        
        # Calculate key metrics
        key_metrics = self._calculate_metrics()
        if key_metrics:
            report.append("\n📈 KEY METRICS:")
            for k, v in key_metrics.items():
                report.append(f"  • {k:<25}: {v:.3f}s")
            report.append("-" * 60)
            
        return "\n".join(report)

    def _calculate_metrics(self) -> Dict[str, float]:
        """Extract standard metrics like TTFT (Time To First Token)"""
        metrics = {}
        events_map = {e.name: e.timestamp for e in self.events}
        
        # STT Latency
        if "stt_audio_captured" in events_map and "stt_final_transcript" in events_map:
            metrics["STT Processing"] = events_map["stt_final_transcript"] - events_map["stt_audio_captured"]
            
        # LLM Latency (TTFT)
        if "llm_request_start" in events_map and "llm_first_token" in events_map:
            metrics["LLM Time-to-First-Token"] = events_map["llm_first_token"] - events_map["llm_request_start"]
            
        # TTS Latency
        if "tts_request_queued" in events_map and "tts_audio_ready" in events_map:
            metrics["TTS Generation"] = events_map["tts_audio_ready"] - events_map["tts_request_queued"]
            
        # Pipeline Total (Voice End -> Audio Start)
        if "stt_audio_captured" in events_map and "tts_playback_start" in events_map:
            metrics["Total Voice-to-Voice"] = events_map["tts_playback_start"] - events_map["stt_audio_captured"]
            
        return metrics

# Global instance accessor
tracker = LatencyTracker()
