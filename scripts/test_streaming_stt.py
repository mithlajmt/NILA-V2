"""
Test script for async audio streaming and Deepgram streaming STT

This script tests the new streaming pipeline independently.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import Settings
from src.services.speech.audio_capture import AudioCapture, AudioConfig
from src.services.speech.providers.deepgram_streaming_provider import DeepgramStreamingProvider

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_async_audio_capture():
    """Test 1: Async audio streaming"""
    print("\n" + "="*60)
    print("TEST 1: Async Audio Capture")
    print("="*60)
    
    config = AudioConfig(
        sample_rate=16000,
        channels=1,
        vad_aggressiveness=2
    )
    
    capture = AudioCapture(config=config)
    
    print("\n🎤 Testing async audio streaming...")
    print("Speak for a few seconds, then pause for 1.5 seconds to stop.\n")
    
    chunks_collected = 0
    total_bytes = 0
    
    try:
        async for chunk in capture.stream_audio(
            chunk_duration_ms=100,
            timeout=15.0,
            silence_duration=1.5,
            min_speech_duration=0.5
        ):
            chunks_collected += 1
            total_bytes += len(chunk)
            
            if chunks_collected % 10 == 0:
                print(f"  Collected {chunks_collected} chunks ({total_bytes} bytes)")
        
        print(f"\n✅ Audio capture complete!")
        print(f"  Total chunks: {chunks_collected}")
        print(f"  Total bytes: {total_bytes}")
        print(f"  Duration: ~{chunks_collected * 0.1:.1f} seconds")
        
        return total_bytes > 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


async def test_deepgram_streaming():
    """Test 2: Deepgram streaming transcription"""
    print("\n" + "="*60)
    print("TEST 2: Deepgram Streaming STT")
    print("="*60)
    
    # Load settings
    try:
        settings = Settings()
        api_key = settings.DEEPGRAM_API_KEY
        
        if not api_key:
            print("\n⚠️ DEEPGRAM_API_KEY not set in .env file")
            print("   Skipping Deepgram streaming test")
            return False
            
    except Exception as e:
        print(f"\n⚠️ Could not load settings: {e}")
        return False
    
    # Create audio capture
    config = AudioConfig(
        sample_rate=16000,
        channels=1,
        vad_aggressiveness=2
    )
    capture = AudioCapture(config=config)
    
    # Create streaming provider
    provider = DeepgramStreamingProvider(
        api_key=api_key,
        model="nova-2",
        language="en-US",
        smart_format=True,
        interim_results=True,
        endpointing=300
    )
    
    print("\n🎤 Speak now! (pause for 1.5s to stop)\n")
    
    try:
        # Start audio stream
        audio_stream = capture.stream_audio(
            chunk_duration_ms=100,
            timeout=15.0,
            silence_duration=1.5,
            min_speech_duration=0.5
        )
        
        # Stream to Deepgram
        final_text = None
        partial_count = 0
        
        async for result in provider.stream_transcribe(audio_stream):
            if result.is_final:
                final_text = result.text
                print(f"\n✅ FINAL: {final_text}")
                print(f"   Confidence: {result.confidence:.2f}")
            else:
                partial_count += 1
                print(f"🔄 Partial #{partial_count}: {result.text}", end="\r")
        
        print(f"\n\n📊 Results:")
        print(f"  Partial results: {partial_count}")
        print(f"  Final transcript: '{final_text}'")
        
        return final_text is not None
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_pipeline():
    """Test 3: Full streaming pipeline (SpeechRecognizer)"""
    print("\n" + "="*60)
    print("TEST 3: Full Streaming Pipeline")
    print("="*60)
    
    try:
        settings = Settings()
        
        if not settings.DEEPGRAM_API_KEY:
            print("\n⚠️ DEEPGRAM_API_KEY not set, skipping full pipeline test")
            return False
        
        from src.services.speech.speech_recognizer import SpeechRecognizer
        
        recognizer = SpeechRecognizer(settings)
        
        print("\n🎤 Speak now! (using full pipeline)\n")
        
        text = await recognizer.listen_streaming(timeout=15)
        
        if text:
            print(f"\n✅ SUCCESS!")
            print(f"  Transcribed: '{text}'")
            return True
        else:
            print(f"\n⚠️ No speech detected")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 STREAMING STT TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Async audio capture
    results['audio_capture'] = await test_async_audio_capture()
    
    # Test 2: Deepgram streaming
    results['deepgram_streaming'] = await test_deepgram_streaming()
    
    # Test 3: Full pipeline
    results['full_pipeline'] = await test_full_pipeline()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n  Total: {total_passed}/{total_tests} tests passed")
    print("="*60 + "\n")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
