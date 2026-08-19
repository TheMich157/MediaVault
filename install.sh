#!/usr/bin/env bash
# ==============================================================================
# MediaVault • 1-Line Interactive Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/TheMich157/MediaVault/main/install.sh | bash
# ==============================================================================

set -e

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║             ⚡ MediaVault Quick Installer & Setup                ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}[✗] Python 3 is required but not installed. Please install Python 3.10+ first.${NC}"
    exit 1
fi

PY_VER=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[✓] Detected Python $PY_VER${NC}"

# Target install directory
INSTALL_DIR="$HOME/MediaVault"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}[!] MediaVault already exists at $INSTALL_DIR. Updating repository...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    echo -e "${CYAN}[i] Cloning MediaVault repository into $INSTALL_DIR...${NC}"
    git clone https://github.com/TheMich157/MediaVault.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo -e "${CYAN}[i] Creating Python virtual environment...${NC}"
    $PYTHON_CMD -m venv venv
fi

echo -e "${CYAN}[i] Installing/updating dependencies...${NC}"
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet

echo -e "${GREEN}${BOLD}[✓] Installation Complete!${NC}\n"
echo -e "To start MediaVault Web Studio, run:"
echo -e "  ${CYAN}cd $INSTALL_DIR && ./run.sh${NC}\n"

# Ask to launch immediately if interactive
if [ -t 0 ]; then
    read -p "Would you like to start MediaVault Web Studio now? [Y/n] " choice
    choice=${choice:-Y}
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        ./run.sh
    fi
fi
