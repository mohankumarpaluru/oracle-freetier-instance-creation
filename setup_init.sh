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

# Function to send Discord message
send_discord_message() {
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -H "Content-Type: application/json" -X POST -d "{\"content\":\"$1\"}" $DISCORD_WEBHOOK
    fi
}

# Load environment variables
source oci.env

# Run the Python program in the background
nohup python3 main.py > /dev/null 2>&1 &

# Store the PID of the background process
SCRIPT_PID=$!

# Function to check if the script is still running
is_script_running() {
    if ps -p $SCRIPT_PID > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check for the existence of ERROR_IN_CONFIG.log after running the Python program
sleep 5  # Wait for a few seconds to allow the program to run and create the log file (if applicable)
if [ -s "ERROR_IN_CONFIG.log" ]; then
    echo "Error occurred, check ERROR_IN_CONFIG.log and rerun the script"
    send_discord_message "😕 Uh-oh! There's an error in the config. Check ERROR_IN_CONFIG.log and give it another shot!"
elif [ -s "INSTANCE_CREATED" ]; then
    echo "Instance created or Already existing has reached Free tier limit. Check 'INSTANCE_CREATED' File"
    send_discord_message "🎊 Great news! An instance was created or we've hit the Free tier limit. Check the 'INSTANCE_CREATED' file for details!"
elif [ -s "launch_instance.log" ]; then
    echo "Script is running successfully"
    send_discord_message "👍 All systems go! The script is running smoothly."
else
    echo "Couldn't find any logs waiting 60 secs before checking again"  
    sleep 60  # Wait for a 1 min to see if the file is populated
    if [ -s "launch_instance.log" ]; then
        echo "Script is running successfully"
        send_discord_message "👍 Good news! The script is up and running after a short delay."
    else
        echo "Unhandled Exception Occurred."
        send_discord_message "😱 Yikes! An unhandled exception occurred. Time to put on the detective hat!"
    fi
fi

# Monitor the script and send a message when it stops
while is_script_running; do
    sleep 60
done

send_discord_message "🛑 Heads up! The OCI Instance Creation Script has stopped running."

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
