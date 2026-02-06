#!/bin/bash
# Run the NILA robot with GPIO access (requires sudo)
cd /home/learnlogicai/Desktop/NILA-V2
source venv/bin/activate
exec python3 main.py "$@"
