#!/usr/bin/env python3
"""
Setup script for Vosk Speech Recognition
Downloads the Vosk model for English-Indian accent.
"""

import os
import sys
import zipfile
import urllib.request
from pathlib import Path

# Configuration
VOSK_MODEL_NAME = "vosk-model-small-en-in-0.4"
VOSK_MODEL_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "models" / "vosk"

def download_file(url, dest_path):
    """Download a file with progress bar"""
    print(f"⬇️  Downloading {url}...")
    try:
        with urllib.request.urlopen(url) as response, open(dest_path, 'wb') as out_file:
            total_size = int(response.getheader('Content-Length', 0))
            block_size = 8192
            downloaded = 0
            
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                
                if total_size > 0:
                    percent = downloaded * 100 / total_size
                    sys.stdout.write(f"\r   Progress: {percent:.1f}%")
                    sys.stdout.flush()
        print("\n✅ Download complete.")
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        sys.exit(1)

def setup_vosk():
    """Main setup function"""
    print("🚀 Setting up Vosk Speech Recognition...")
    
    # 1. Create directories
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Check if model already exists
    model_path = MODELS_DIR / VOSK_MODEL_NAME
    if model_path.exists():
        print(f"✅ Vosk model already exists at {model_path}")
        return
    
    # 3. Download model
    zip_path = MODELS_DIR / f"{VOSK_MODEL_NAME}.zip"
    download_file(VOSK_MODEL_URL, zip_path)
    
    # 4. Extract model
    print("📦 Extracting Vosk model...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(MODELS_DIR)
        print("✅ Extraction complete.")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)
    
    # 5. Cleanup zip file
    os.remove(zip_path)
    print(f"✅ Vosk model installed at {model_path}")
    
    print("\n🎉 Vosk setup complete!")
    print(f"   Model: {model_path}")

if __name__ == "__main__":
    setup_vosk()
