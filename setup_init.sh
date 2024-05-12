#!/bin/bash

# Check if any log files exist
if ls *.log >/dev/null 2>&1; then
    # Delete existing log files
    rm -f *.log
    echo "Previous Log files deleted."
fi

# Making environment non-interactive
export DEBIAN_FRONTEND=noninteractive

# Check if the argument is 'rerun'
if [ "$1" != "rerun" ]; then
    # Update package lists and install required packages without confirmation
    sudo apt update -y
    sudo apt install python3-venv -y
    python3 -m venv .venv
fi

source .venv/bin/activate

# Upgrade pip and install necessary packages
if [ "$1" != "rerun" ]; then
    pip install --upgrade pip
    pip install wheel setuptools
    pip install -r requirements.txt
fi

# Run the Python program in the background
nohup python3 main.py > /dev/null 2>&1 &

# Check for the existence of ERROR_IN_CONFIG.log after running the Python program
sleep 5  # Wait for a few seconds to allow the program to run and create the log file (if applicable)
if [ -f "launch_instance.log" ]; then
    echo "Script is running successfully"
elif [ -f "ERROR_IN_CONFIG.log" ]; then
    echo "Error occurred, check ERROR_IN_CONFIG.log and rerun the script"
else
    echo "Unhandled Exception Occurred."
fi

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
