import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.tts.tts_service import TTSService
from src.services.audio.audio_player import AudioPlayer

# Mock Settings
class MockSettings:
    TTS_PROVIDER = "gtts" # Use GTTS for simple test
    GTTS_TLD = "co.in"
    GTTS_SLOW = False
    GTTS_LANG = "en"
    SERIAL_PORT = "/dev/ttyUSB0"
    SERIAL_BAUD = 115200

async def test_decoupled_flow():
    print("🧪 Testing Decoupled Architecture...")
    
    settings = MockSettings()
    
    # Mock Hardware Controller
    mock_hardware = MagicMock()
    mock_hardware.send_jaw_intensity = MagicMock()
    
    # Mock AudioPlayer (we don't want to actually play audio in CI/Cloud)
    # But we want to verify it calls the callback
    
    # We need to patch pygame in AudioPlayer to avoid init errors if no audio device
    with patch('src.services.audio.audio_player.pygame') as mock_pygame:
        mock_pygame.mixer.get_init.return_value = True
        mock_pygame.mixer.music.get_busy.side_effect = [True, True, False] # Simulate playing for a bit
        
        audio_player = AudioPlayer()
        
        # Initialize TTSService
        tts_service = TTSService(settings)
        
        print(f"✅ TTSService initialized with {tts_service.get_provider_info()}")
        
        # Mock generate_audio and _play_audio to return fake paths/futures
        with patch.object(tts_service.provider, '_generate_audio', return_value=MagicMock()) as mock_generate, \
             patch.object(tts_service.provider, '_play_audio', new_callable=MagicMock) as mock_play:
            mock_generate.return_value.exists.return_value = True
            mock_generate.return_value.name = "test.mp3"
            mock_play.return_value = asyncio.Future()
            mock_play.return_value.set_result(None)
            
            # Test Speak
            print("🗣️  Calling speak('Hello world')...")
            await tts_service.speak("Hello world")
            
            # Verify generate_audio and play_audio were called
            mock_generate.assert_called_once()
            print("✅ _generate_audio called")
            
            mock_play.assert_called_once()
            print("✅ _play_audio called")
            print("✅ Decoupled flow verified!")

if __name__ == "__main__":
    asyncio.run(test_decoupled_flow())
