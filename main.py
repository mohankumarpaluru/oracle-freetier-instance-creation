import logging
import os
import time
from pathlib import Path

import oci
import paramiko
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('oci.env')

# Access loaded environment variables
OCI_CONFIG = os.getenv("OCI_CONFIG")
OCI_USER_ID = os.getenv("OCI_USER_ID")
OCT_FREE_AD = os.getenv("OCT_FREE_AD")
DISPLAY_NAME = os.getenv("DISPLAY_NAME")
SSH_AUTHORIZED_KEYS_FILE = os.getenv("SSH_AUTHORIZED_KEYS_FILE")

# Set up logging
logging.basicConfig(
    filename="step1to4.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logging_step5 = logging.getLogger("step5")
logging_step5.setLevel(logging.INFO)
fh = logging.FileHandler("step5.log")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging_step5.addHandler(fh)

# Set up OCI Config and Clients
oci_config_path = OCI_CONFIG if OCI_CONFIG else "~/.oci/config"
config = oci.config.from_file(oci_config_path)
iam_client = oci.identity.IdentityClient(config)
network_client = oci.core.VirtualNetworkClient(config)
compute_client = oci.core.ComputeClient(config)


def create_instance_details_file(compartment_id):
    list_instances_response = compute_client.list_instances(compartment_id=compartment_id)
    for instance in list_instances_response.data:
        if instance.shape == "VM.Standard.A1.Flex":
            with open('INSTANCE_CREATED', 'w') as file:
                details = [f"Instance ID: {instance.id}",
                           f"Display Name: {instance.display_name}",
                           f"Availability Domain: {instance.availability_domain}",
                           f"Shape: {instance.shape}",
                           f"State: {instance.lifecycle_state}",
                           "\n"]
                file.write('\n'.join(details))


def handle_errors(command, data, log):
    """
    Handles errors and logs messages.

    Parameters:
        command (str): The OCI command being executed.
        data (dict): The data or error information returned from the OCI service.
        log (logging.Logger): The logger instance for logging messages.

    Raises:
        Exception: Raises an exception if an unexpected error occurs.
    """
    log.info("Command: %s\nOutput: %s", command, data)
    if "code" in data:
        error_code = data["code"]
        if error_code in ("Out Of Capacity", "TooManyRequests"):
            time.sleep(60)
            return True
    raise Exception("Error: %s" % data)


def execute_oci_command(client, method, *args, **kwargs):
    """
    Executes an OCI command using the specified OCI client.

    Parameters:
        client: The OCI client instance.
        method (str): The method to call on the OCI client.
        args: Additional positional arguments to pass to the OCI client method.
        kwargs: Additional keyword arguments to pass to the OCI client method.

    Returns:
        dict: The data returned from the OCI service.

    Raises:
        Exception: Raises an exception if an unexpected error occurs.
    """
    while True:
        try:
            response = getattr(client, method)(*args, **kwargs)
            data = response.data if hasattr(response, "data") else response
            return data
        except oci.exceptions.ServiceError as err:
            handle_errors(args, err.service_error, logging)


def generate_ssh_key_pair(public_key_file, private_key_file):
    """
    Generates an SSH key pair and saves them to the specified files.

    Parameters:
        public_key_file (str): The file to save the public key.
        private_key_file (str): The file to save the private key.
    """
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(private_key_file)
    # Save public key to file
    with open(public_key_file, "w", encoding="utf-8") as pub_key:
        pub_key.write(f"ssh-rsa {key.get_base64()} {public_key_file.stem}_auto_generated")


def read_or_generate_ssh_public_key(public_key_file):
    """
    Reads the SSH public key from the file if it exists, else generates and reads it.

    Parameters:
        public_key_file (str): The file containing the public key.

    Returns:
        str: The SSH public key.
    """
    public_key_path = Path(public_key_file)

    if not public_key_path.is_file():
        logging.info("SSH key doesn't exist... Generating SSH Key Pair")
        public_key_path.parent.mkdir(parents=True, exist_ok=True)
        private_key_path = public_key_path.with_name(f"{public_key_path.stem}_private{public_key_path.suffix}")
        generate_ssh_key_pair(public_key_path, private_key_path)

    with open(public_key_path, "r", encoding="utf-8") as pub_key_file:
        ssh_public_key = pub_key_file.read()

    return ssh_public_key


def launch_instance():
    """
    Launches an OCI Compute instance using the specified parameters.

    Raises:
        Exception: Raises an exception if an unexpected error occurs.
    """
    # Step 1 - Get TENANCY
    user_info = execute_oci_command(iam_client, "get_user", OCI_USER_ID)
    oci_tenancy = user_info.compartment_id
    logging.info("OCI_TENANCY: %s", oci_tenancy)

    # Step 2 - Get AD Name
    availability_domains = execute_oci_command(iam_client,
                                               "list_availability_domains",
                                               compartment_id=oci_tenancy)
    oci_ad_name = next(item.name for item in availability_domains if item.name.endswith(OCT_FREE_AD))

    logging.info("OCI_AD_NAME: %s", oci_ad_name)

    # Step 3 - Get Subnet ID
    subnets = execute_oci_command(network_client,
                                  "list_subnets",
                                  compartment_id=oci_tenancy)
    oci_subnet_id = subnets[0].id
    logging.info("OCI_SUBNET_ID: %s", oci_subnet_id)

    # Step 4 - Get Image ID of VM.Standard.A1.Flex
    images = execute_oci_command(
        compute_client,
        "list_images",
        compartment_id=oci_tenancy,
        shape="VM.Standard.A1.Flex",
    )
    oci_image_id = images[0].id
    logging.info("OCI_IMAGE_ID: %s", oci_image_id)

    ssh_public_key = read_or_generate_ssh_public_key(SSH_AUTHORIZED_KEYS_FILE)

    # Step 5 - Launch Instance
    while True:
        try:
            launch_instance_response = compute_client.launch_instance(
                launch_instance_details=oci.core.models.LaunchInstanceDetails(
                    availability_domain=oci_ad_name,
                    compartment_id=oci_tenancy,
                    create_vnic_details=oci.core.models.CreateVnicDetails(
                        assign_public_ip=False,
                        assign_private_dns_record=True,
                        display_name=DISPLAY_NAME,
                        subnet_id=oci_subnet_id,
                    ),
                    display_name=DISPLAY_NAME,
                    shape="VM.Standard.A1.Flex",
                    image_id=oci_image_id,
                    availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(
                        recovery_action="RESTORE_INSTANCE"
                    ),
                    instance_options=oci.core.models.InstanceOptions(
                        are_legacy_imds_endpoints_disabled=False
                    ),
                    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                        ocpus=4, memory_in_gbs=24
                    ),
                    metadata={
                        "ssh_authorized_keys": ssh_public_key},
                )
            )
            if launch_instance_response.status == 200:
                logging_step5.info(
                    "Command: launch_instance\nOutput: %s", launch_instance_response
                )
                break

        except oci.exceptions.ServiceError as srv_err:
            if srv_err.code == "LimitExceeded":
                logging_step5.info("LimitExceeded , exiting the program")
                create_instance_details_file(oci_tenancy)
                exit()
            data = {
                "status": srv_err.status,
                "code": srv_err.code,
                "message": srv_err.message,
            }
            handle_errors("launch_instance", data, logging_step5)


if __name__ == "__main__":
    launch_instance()
