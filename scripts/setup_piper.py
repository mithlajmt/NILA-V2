#!/usr/bin/env python3
"""
Setup script for Piper TTS
Downloads the appropriate binary and voice model for the current system.
"""

import os
import sys
import platform
import tarfile
import urllib.request
import shutil
from pathlib import Path

# Configuration
PIPER_VERSION = "2023.11.14-2"
VOICE_NAME = "ml_IN-arjun-medium"
VOICE_FILE = f"{VOICE_NAME}.onnx"
VOICE_CONFIG = f"{VOICE_NAME}.onnx.json"

# URLs
# 2023.11.14-2 is a stable release
BASE_URL = f"https://github.com/rhasspy/piper/releases/download/{PIPER_VERSION}"
# Note: The URL structure for voices might vary. For ml_IN, it is in the ml/ml_IN directory.
VOICE_URL = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ml/ml_IN/arjun/medium/{VOICE_FILE}"
VOICE_CONFIG_URL = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ml/ml_IN/arjun/medium/{VOICE_CONFIG}"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"
MODELS_DIR = PROJECT_ROOT / "data" / "models" / "piper"

def get_system_arch():
    """Get the system architecture for Piper binary"""
    machine = platform.machine().lower()
    system = platform.system().lower()
    
    if system != "linux":
        print(f"⚠️  Warning: This script is designed for Linux. Detected: {system}")
        # Fallback to trying linux binaries or exit? Let's try to proceed if it's mostly compatible or warn user.
        # Piper releases are mostly Linux/macOS/Windows.
    
    if machine in ["x86_64", "amd64"]:
        return "amd64"
    elif machine in ["aarch64", "arm64"]:
        return "arm64"
    elif machine.startswith("armv7"):
        return "armv7"
    else:
        print(f"❌ Unsupported architecture: {machine}")
        sys.exit(1)

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

def setup_piper():
    """Main setup function"""
    print("🚀 Setting up Piper TTS...")
    
    # 1. Create directories
    TOOLS_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Determine binary URL
    arch = get_system_arch()
    if arch == "amd64":
        binary_name = "piper_linux_x86_64.tar.gz"
    elif arch == "arm64":
        binary_name = "piper_linux_aarch64.tar.gz"
    elif arch == "armv7":
        binary_name = "piper_linux_armv7l.tar.gz"
    
    binary_url = f"{BASE_URL}/{binary_name}"
    
    piper_dir = TOOLS_DIR / "piper"
    piper_exe = piper_dir / "piper"
    
    # 3. Download and extract binary if not exists
    if not piper_exe.exists():
        print(f"📦 Detected architecture: {arch}")
        tar_path = TOOLS_DIR / binary_name
        download_file(binary_url, tar_path)
        
        print("📦 Extracting Piper...")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=TOOLS_DIR)
        
        # Cleanup tar
        os.remove(tar_path)
        print("✅ Piper binary installed.")
    else:
        print("✅ Piper binary already exists.")

    # 4. Download voice model
    model_path = MODELS_DIR / VOICE_FILE
    config_path = MODELS_DIR / VOICE_CONFIG
    
    if not model_path.exists():
        print(f"🗣️  Downloading voice model: {VOICE_NAME}")
        download_file(VOICE_URL, model_path)
    else:
        print("✅ Voice model already exists.")
        
    if not config_path.exists():
        print(f"📄 Downloading voice config...")
        download_file(VOICE_CONFIG_URL, config_path)
    else:
        print("✅ Voice config already exists.")

    print("\n🎉 Piper setup complete!")
    print(f"   Binary: {piper_exe}")
    print(f"   Model:  {model_path}")
    print("\nTo test, run:")
    print(f"   echo 'Hello world' | {piper_exe} --model {model_path} --output_file test.wav")

if __name__ == "__main__":
    setup_piper()
