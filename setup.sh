#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}     NILA-V2 Automated Setup Script      ${NC}"
echo -e "${BLUE}=========================================${NC}"

# 1. System Updates & Dependencies
echo -e "\n${GREEN}[1/6] Installing System Dependencies...${NC}"
if [ -f /etc/debian_version ]; then
    echo "Detected Debian/Ubuntu/Raspberry Pi OS"
    sudo apt update
    sudo apt install -y python3-pip python3-venv git portaudio19-dev libasound2-dev libespeak1 ffmpeg
else
    echo -e "${RED}Warning: Non-Debian system detected. Please install dependencies manually:${NC}"
    echo "python3-pip, python3-venv, git, portaudio19-dev, libasound2-dev, libespeak1, ffmpeg"
    read -p "Press Enter to continue..."
fi

# 2. Python Virtual Environment
echo -e "\n${GREEN}[2/6] Setting up Python Environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created virtual environment."
else
    echo "Virtual environment already exists."
fi

# Activate venv
source venv/bin/activate

# 3. Python Dependencies
echo -e "\n${GREEN}[3/6] Installing Python Dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 4. Setup Models (Piper)
echo -e "\n${GREEN}[4/6] Downloading AI Models...${NC}"
# Make scripts executable
chmod +x scripts/*.py

echo "Running Piper TTS setup..."
python3 scripts/setup_piper.py

# 5. Configuration
echo -e "\n${GREEN}[5/6] Configuration...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo "Created .env from template."
        echo -e "${BLUE}Please edit .env with your specific settings!${NC}"
    else
        echo -e "${RED}Warning: .env.template not found!${NC}"
    fi
else
    echo ".env file already exists."
fi

# 6. Permissions
echo -e "\n${GREEN}[6/6] Setting Permissions...${NC}"
# Add user to dialout group for Arduino access if on Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! groups | grep -q "dialout"; then
        echo "Adding user to 'dialout' group for Serial/Arduino access..."
        sudo usermod -a -G dialout $USER
        echo -e "${BLUE}Note: You may need to logout/login for group changes to take effect.${NC}"
    fi
fi

echo -e "\n${BLUE}=========================================${NC}"
echo -e "${GREEN}       Setup Complete! 🚀               ${NC}"
echo -e "${BLUE}=========================================${NC}"
echo -e "To start the robot:"
echo -e "1. Edit .env file with your API keys and settings"
echo -e "2. Run: ${GREEN}source venv/bin/activate${NC}"
echo -e "3. Run: ${GREEN}python main.py${NC}"
