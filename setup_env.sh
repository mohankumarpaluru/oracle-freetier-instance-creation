#!/usr/bin/env bash

# oci_config_setup.sh
# This script sets up the OCI configuration interactively and creates an oci.env file.

display_choices(){
cat <<EOF
Choose one of the two free shapes

1. VM.Standard.A1.Flex
2. VM.Standard.E2.1.Micro
EOF
}

read -p "Type name of the instance: " INSTANCE_NAME
clear

while true; do
    display_choices
    
    read -p "Enter your choice (1 or 2): " SHAPE
    
    case $SHAPE in
        1)
            SHAPE="VM.Standard.A1.Flex"
            break
            ;;
        2)
            SHAPE="VM.Standard.E2.1.Micro"
            break
            ;;
        *)
            clear
            echo "Invalid choice. Please try again. (CTRL+C to quit)"
            ;;
    esac
done
clear

while true; do
    read -p "Use the script for your second free tier Micro Instance? (y/n): " BOOL_MICRO
    
    BOOL_MICRO=$(echo "$BOOL_MICRO" | tr '[:upper:]' '[:lower:]')

    case $BOOL_MICRO in
        y)
            BOOL_MICRO="True"
            break
            ;;
        n)
            BOOL_MICRO="False"
            break
            ;;
        *)
            clear
            echo "Invalid choice. Please try again (CTRL+C to quit)"
            ;;
    esac
done
clear

read -p "Enter the Subnet OCID (or press Enter to skip): " SUBNET_ID
clear

read -p "Enter the Image OCID (or press Enter to skip): " IMAGE_ID
clear

while true; do
    read -p "Enable Gmail notification? (y/n): " BOOL_MAIL
    
    BOOL_MAIL=$(echo "$BOOL_MAIL" | tr '[:upper:]' '[:lower:]')

    case $BOOL_MAIL in
        y)
            BOOL_MAIL="True"
            break
            ;;
        n)
            BOOL_MAIL="False"
            break
            ;;
        *)
            clear
            echo "Invalid choice. Please try again (CTRL+C to quit)"
            ;;
    esac
done
clear

if [[ $BOOL_MAIL == "True" ]]; then
    read -p "Enter your email: " EMAIL
    clear

    read -p "Enter email app password (16 characters without spaces): " EMAIL_PASS
    clear
fi

read -p "Enter Discord webhook URL (or press Enter to skip): " DISCORD_WEBHOOK
clear

read -p "Enter Telegram bot token (or press Enter to skip): " TELEGRAM_TOKEN
clear

read -p "Enter Telegram user ID (or press Enter to skip): " TELEGRAM_USER_ID
clear

# Backup existing oci.env if it exists
if [ -f oci.env ]; then
    mv oci.env oci.env.bak
    echo "Existing oci.env file backed up as oci.env.bak"
fi

# Create the new oci.env file with the gathered configuration
cat <<EOF > oci.env
# OCI Configuration
OCI_CONFIG=$HOME/oracle-freetier-instance-creation/oci_config
OCT_FREE_AD=AD-1
DISPLAY_NAME=$INSTANCE_NAME
# The other free shape is AMD: VM.Standard.E2.1.Micro
OCI_COMPUTE_SHAPE=$SHAPE
SECOND_MICRO_INSTANCE=$BOOL_MICRO
REQUEST_WAIT_TIME_SECS=60
SSH_AUTHORIZED_KEYS_FILE=$HOME/oracle-freetier-instance-creation/id_rsa.pub
# SUBNET_ID to use ONLY in case running in local or a non E2.1.Micro instance 
OCI_SUBNET_ID=$SUBNET_ID
OCI_IMAGE_ID=$IMAGE_ID
# The following will be ignored if OCI_IMAGE_ID is specified
OPERATING_SYSTEM=Canonical Ubuntu
OS_VERSION=22.04

# Gmail Notification
NOTIFY_EMAIL=$BOOL_MAIL
EMAIL=$EMAIL
EMAIL_PASSWORD=$EMAIL_PASS

# Discord Notification (optional)
DISCORD_WEBHOOK=$DISCORD_WEBHOOK

# Telegram Notification (optional)
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
TELEGRAM_USER_ID=$TELEGRAM_USER_ID
EOF

echo "OCI env configuration saved to oci.env"
