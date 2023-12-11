
# Oracle Free Tier Instance Creation Through Python

This project provides a Python script and shell scripts to automate the creation of Oracle Free Tier ARM instances (4 OCPU, 24 GB RAM) with minimal manual intervention. Acquiring resources in certain availability domains can be challenging due to high demand, and repeatedly attempting creation through the Oracle console is impractical. While other methods like OCI CLI and PHP are available (linked at the end), this solution aims to streamline the process by implementing it in Python.

The script attempts to create an instance every 60 seconds or as per the `REQUEST_WAIT_TIME_SECS` variable specified in the `oci.env` file until the instance is successfully created. Upon completion, a file named `INSTANCE_CREATED` is generated in the project directory, containing details about the newly created instance. Additionally, you can configure the script to send a Gmail notification upon instance creation.

This script doesn't configure public IP by default, you need to configure it post the creation of the instance from console. 

## Features
- Single File needs to be run after basic setup
- Configurable Wait Time , OCPU, RAM, DISPLAY_NAME
- Gmail Notification
- SSH Keys for ARM instance can be automatically created
- OS Configuration based on Image ID or OS and Version	

## Pre-Requisites
- **V2 Instance**: The script is designed for a Ubuntu environment, and you need an existing subnet ID for ARM instance creation. Create an always-free **V2 instance** with Ubuntu 22.04. This instance can be deleted after the ARM instance creation.
- **OCI API Key (Private Key) & Config Details**: Follow the provided link to create the necessary API key and config details.
- **OCI Free Availability Domain**: Identify the eligible always-free tier availability domain during instance creation.
- **Gmail App Passkey (Optional)**: If you want to receive an email notification after instance creation and have two-factor authentication enabled, follow the provided link to create a custom app and obtain the passkey.

## Setup

1. SSH into the V2 Ubuntu machine, clone this repository, and navigate to the project directory. Change the permissions of `setup_init.sh` to make it executable.
    ```bash
    git clone https://github.com/mohankumarpaluru/oracle-freetier-instance-creation.git
    cd oracle-freetier-instance-creation
    chmod +x setup_init.sh
    ```

2. Create a file named `oci_api_private_key.pem` and paste the contents of your API private key. The name and path of the file can be anything, but the current user should have read access.

3. Create a file named `oci_config` inside the repository directory. Paste the config details copied during the OCI API key creation. Refer to `sample_oci_config`.

4. In your `oci_config`, fill the **`key_path`** with the absolute path of your `oci_api_private_key.pem`. For example, `\home\ubuntu\oracle-freetier-instance-creation\oci_api_private_key.pem`.

5. Edit the **`oci.env`** file and fill in the necessary details. Refer to the documentation for more information on `oci.env` fields.

## Run

Once the setup is complete, run the `setup_init.sh` script from the project directory. This script installs the required dependencies and starts the Python program in the background.
```bash
./setup_init.sh
```
View the logs of the instance creation API call in `launch_instance.log` and details about the parameters used (availability-domain, compartment-id, subnet-id, image-id) `setup_and_info.log`.
