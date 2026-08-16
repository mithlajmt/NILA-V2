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
        tts_service = TTSService(settings, audio_player, mock_hardware)
        
        print(f"✅ TTSService initialized with {tts_service.get_provider_info()}")
        
        # Mock generate_audio to return a fake path so we don't need network/files
        with patch.object(tts_service.provider, 'generate_audio', return_value=MagicMock()) as mock_generate:
            mock_generate.return_value.exists.return_value = True
            mock_generate.return_value.name = "test.mp3"
            
            # Test Speak
            print("🗣️  Calling speak('Hello world')...")
            await tts_service.speak("Hello world")
            
            # Verify generate_audio was called
            mock_generate.assert_called_once()
            print("✅ generate_audio called")
            
            # Verify audio_player.play was called with callback
            # We can't easily mock the async method of the instance we just created without more patching,
            # but we can check if hardware callback was passed if we mock AudioPlayer.play
            
            # Let's try a more integration-style test where we let AudioPlayer.play run (mocked pygame)
            # and see if it tries to play.
            
            mock_pygame.mixer.music.load.assert_called()
            mock_pygame.mixer.music.play.assert_called()
            print("✅ AudioPlayer.play triggered pygame")
            
            # Since we mocked pygame, the _play_with_analysis loop in AudioPlayer won't run effectively 
            # unless we mock wave.open etc. 
            # But we verified the wiring: TTSService -> AudioPlayer -> Pygame
            
            print("✅ Decoupled flow verified!")

if __name__ == "__main__":
    asyncio.run(test_decoupled_flow())
