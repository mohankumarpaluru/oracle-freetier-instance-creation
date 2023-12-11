
# Oracle Free Tier Instance Creation Through Python

This project provides a Python script and shell scripts to automate the creation of Oracle Free Tier ARM instances (4 OCPU, 24 GB RAM) with minimal manual intervention. Acquiring resources in certain availability domains can be challenging due to high demand, and repeatedly attempting creation through the Oracle console is impractical. While other methods like OCI CLI and PHP are available (linked at the end), this solution aims to streamline the process by implementing it in Python.

The script attempts to create an instance every 60 seconds or as per the `REQUEST_WAIT_TIME_SECS` variable specified in the `oci.env` file until the instance is successfully created. Upon completion, a file named `INSTANCE_CREATED` is generated in the project directory, containing details about the newly created instance. Additionally, you can configure the script to send a Gmail notification upon instance creation.

**This script doesn't configure a public IP by default; you need to configure it post the creation of the instance from the console.(Planning on automating it soon)**

## Features
- Single File needs to be run after basic setup
- Configurable Wait Time , OCPU, RAM, DISPLAY_NAME
- Gmail Notification
- SSH Keys for ARM instance can be automatically created
- OS Configuration based on Image ID or OS and Version	

## Pre-Requisites
- **VM.Standard.E2.1.Micro Instance**: The script is designed for a Ubuntu environment, and you need an existing subnet ID for ARM instance creation. Create an always-free `VM.Standard.E2.1.Micro` instance with Ubuntu 22.04. This instance can be deleted after the ARM instance creation.
- **OCI API Key (Private Key) & Config Details**: Follow this <TODO> to create the necessary API key and config details.
- **OCI Free Availability Domain**: Identify the eligible always-free tier availability domain during instance creation.
- **Gmail App Passkey (Optional)**: If you want to receive an email notification after instance creation and have two-factor authentication enabled, follow this <TODO> to create a custom app and obtain the passkey.

## Setup

1. SSH into the VM.Standard.E2.1.Micro Ubuntu machine, clone this repository, and navigate to the project directory. Change the permissions of `setup_init.sh` to make it executable.
    ```bash
    git clone https://github.com/mohankumarpaluru/oracle-freetier-instance-creation.git
    cd oracle-freetier-instance-creation
    chmod +x setup_init.sh
    ```

2. Create a file named `oci_api_private_key.pem` and paste the contents of your API private key. The name and path of the file can be anything, but the current user should have read access.

3. Create a file named `oci_config` inside the repository directory. Paste the config details copied during the OCI API key creation. Refer to `sample_oci_config`.

4. In your `oci_config`, fill the **`key_file`** with the absolute path of your `oci_api_private_key.pem`. For example, `\home\ubuntu\oracle-freetier-instance-creation\oci_api_private_key.pem`.

5. Edit the **`oci.env`** file and fill in the necessary details. Refer [below for more information](https://github.com/mohankumarpaluru/oracle-freetier-instance-creation#environment-variables) `oci.env` fields.

## Run

Once the setup is complete, run the `setup_init.sh` script from the project directory. This script installs the required dependencies and starts the Python program in the background.
```bash
./setup_init.sh
```
If you are running in a fresh `VM.Standard.E2.1.Micro`  instance, you might receive a prompt *Daemons using outdated libraries* prompt just click `OK` , that's due to updating the libraries through apt update and wont be asked again. 

View the logs of the instance creation API call in `launch_instance.log` and details about the parameters used (availability-domain, compartment-id, subnet-id, image-id) `setup_and_info.log`.



## TODO
- Make Block Volume Size configurable and handle errors
- Assign public IP through script 
- Creating list of images and OS to display before launching instance to select


## Environment Variables
**Required Fields :**
	
- `OCI_CONFIG`:  Absolute path to the file with OCI API Config Detail content 
- `OCT_FREE_AD`: Availability Domain that's eligible for *Always-Free Tier*

**Optional Fields :**
- `DISPLAY_NAME`: Name of the Instance 
- `REQUEST_WAIT_TIME_SECS`: Wait before trying to launch instance again.  
- `SSH_AUTHORIZED_KEYS_FILE`: Give absolute path of a SSH public for ARM instance, **Program will create a public and private key pair with name specified if the key file doesn't exit else uses the one specified** ,  
- `OCI_IMAGE_ID`: *Image_id* of the file desired os and version, the script will generate the image_list.json` 
- `OPERATING_SYSTEM`: Exact name of the operating system 
- `OS_VERSION`: Exact version of the operating system 
- `NOTIFY_EMAIL`: Make it True if you want to get notified and provide email and password
- `EMAIL`: Only Gmail is allowed, same email will be used for *FROM* an *TO*
- `EMAIL_PASSWORD`: If two factor authentication is set, create an App Password and specify it not the email password. Direct password will work if no two factor authentication is configured for the email.


## Credits and References
- [xitroff](https://www.reddit.com/user/xitroff/): [Resolving Oracle Cloud Out of Capacity Issue and Getting Free VPS with 4 ARM Cores, 24GB of RAM](https://hitrov.medium.com/resolving-oracle-cloud-out-of-capacity-issue-and-getting-free-vps-with-4-arm-cores-24gb-of-a3d7e6a027a8)
- [Oracle Launch Instance Docs](https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/Instance/LaunchInstance)
- [LaunchInstanceDetails](https://docs.oracle.com/en-us/iaas/api/#/en/iaas/20160918/datatypes/LaunchInstanceDetails)
