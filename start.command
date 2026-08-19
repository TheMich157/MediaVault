#!/usr/bin/env bash

# Change directory to the folder where this script is located
cd -- "$(dirname -- "$0")"

clear
echo "============================================================"
echo "    Launching MediaVault • Insta & TikTok Downloader Studio "
echo "============================================================"
echo ""

# Ensure virtual environment and dependencies
if [ ! -d "venv" ]; then
    echo "First time setup: Installing dependencies in virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# Launch the Web Studio
./venv/bin/python main.py
