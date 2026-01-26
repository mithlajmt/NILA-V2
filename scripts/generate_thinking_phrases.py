import os
import subprocess
from pathlib import Path

def generate_fillers():
    # Configuration
    piper_binary = Path("tools/piper/piper").resolve()
    model_dir = Path("tools/piper/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_name = "en_US-ryan-medium.onnx"
    model_path = model_dir / model_name
    json_path = model_dir / f"{model_name}.json"
    
    # Download model if missing
    if not model_path.exists() or not json_path.exists():
        print("⬇️ Downloading Piper model (Male - Ryan)...")
        import urllib.request
        
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/medium"
        
        try:
            if not model_path.exists():
                print(f"   Downloading {model_name}...")
                urllib.request.urlretrieve(f"{base_url}/{model_name}?download=true", model_path)
                
            if not json_path.exists():
                print(f"   Downloading {model_name}.json...")
                urllib.request.urlretrieve(f"{base_url}/{model_name}.json?download=true", json_path)
                
            print("✅ Model downloaded.")
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return

    output_dir = Path("data/audio/sfx/thinking")
    # Clean up old files
    if output_dir.exists():
        for f in output_dir.glob("*.wav"):
            f.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Single long phrase as requested
    phrase = "Hmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm"
    
    print(f"🎤 Generating long filler using model: {model_path.name}")
    
    filename = output_dir / "thinking_long.wav"
    
    # Command: echo 'Phrase' | piper ...
    cmd = [
        str(piper_binary),
        "--model", str(model_path),
        "--output_file", str(filename),
        "--length_scale", "2.0", # Very slow
        "--noise_scale", "0.667",
        "--noise_w", "0.8"
    ]
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=phrase.encode())
        
        if process.returncode == 0:
            print(f"✅ Generated: {filename}")
        else:
            print(f"❌ Failed to generate: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_fillers()
