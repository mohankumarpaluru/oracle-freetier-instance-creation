#!/bin/bash

# Making environment non-interactive
export DEBIAN_FRONTEND=noninteractive

# Check if the argument is 'rerun'
if [ "$1" != "rerun" ]; then
    # Update package lists and install required packages without confirmation
    sudo apt update -y
    sudo apt install python3-venv -y
fi

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install necessary packages
if [ "$1" != "rerun" ]; then
    pip install --upgrade pip
    pip install wheel setuptools
    pip install -r requirements.txt
fi

# Run the Python program in the background
nohup python3 main.py > /dev/null 2>&1 &

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
