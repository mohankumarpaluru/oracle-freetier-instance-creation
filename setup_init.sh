#!/bin/bash

# Making environment non interactive
export DEBIAN_FRONTEND=noninteractive

# Update package lists and install required packages without confirmation
sudo apt update -y
sudo apt install python3-venv -y

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install necessary packages
pip install --upgrade pip
pip install wheel setuptools
pip install -r requirements.txt

# Run the Python program in the background
nohup python3 main.py > /dev/null 2>&1 &

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
