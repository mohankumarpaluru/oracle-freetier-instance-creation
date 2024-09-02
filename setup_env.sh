#!/bin/bash

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
    
    if [[ $SHAPE == "1" ]]; then
        SHAPE="VM.Standard.A1.Flex"
        break 
    elif [[ $SHAPE == "2" ]]; then
        SHAPE="VM.Standard.E2.1.Micro"
        break 
    else
        clear
        echo "Invalid choice. Please try again. (CTRL+C to quit)"
    fi
done
clear

read -p "Enter the Subnet OCID (or press Enter to skip): " SUBNET_ID
clear

read -p "Enter the Image OCID (or press Enter to skip): " IMAGE_ID
clear

while true; do
    read -p "Enable gmail notification? (y/n): " BOOL_MAIL
    
    BOOL_MAIL=$(echo "$BOOL_MAIL" | tr '[:upper:]' '[:lower:]')

    if [[ $BOOL_MAIL == "y" ]]; then
        BOOL_MAIL="True"
        break 
    elif [[ $BOOL_MAIL == "n" ]]; then
        BOOL_MAIL="False"
        break 
    else
        clear
        echo "Invalid choice. Please try again (CTRL+C to quit)"
    fi
done
clear

if [[ $BOOL_MAIL == "True" ]]; then
    read -p "Enter your email: " EMAIL
    clear

    read -p "Enter email app password (16 characters without spaces): " EMAIL_PASS
    clear
fi

cat <<EOF > oci.env
# OCI Configuration
OCI_CONFIG=$HOME/oracle-freetier-instance-creation/oci_config
OCT_FREE_AD=AD-1
DISPLAY_NAME=$INSTANCE_NAME
# The other free shape is AMD: VM.Standard.E2.1.Micro
OCI_COMPUTE_SHAPE=VM.Standard.A1.Flex
SECOND_MICRO_INSTANCE=False
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
EOF
