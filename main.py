import configparser
import json
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
OCT_FREE_AD = os.getenv("OCT_FREE_AD")
DISPLAY_NAME = os.getenv("DISPLAY_NAME")
WAIT_TIME = os.getenv("REQUEST_WAIT_TIME_SECS")
SSH_AUTHORIZED_KEYS_FILE = os.getenv("SSH_AUTHORIZED_KEYS_FILE")
BOOT_VOL_SIZE = os.getenv("BOOT_VOLUME_SIZE_IN_GBS")
OCI_IMAGE_ID = os.getenv("OCI_IMAGE_ID")
OPERATING_SYSTEM = os.getenv("OPERATING_SYSTEM")
OS_VERSION = os.getenv("OS_VERSION")

# Read the configuration from oci_config file
config = configparser.ConfigParser()
config.read(OCI_CONFIG)
OCI_USER_ID = config.get('DEFAULT', 'user')

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

IMAGE_LIST_KEYS = [
    "lifecycle_state",
    "display_name",
    "id",
    "operating_system",
    "operating_system_version",
    "size_in_mbs",
    "time_created",
]


def write_into_file(file_path, data):
    """Write data into a file.

    Args:
        file_path (str): The path of the file.
        data (str): The data to be written into the file.
    """
    with open(file_path, "w", encoding="utf-8") as file_writer:
        file_writer.write(data)


def create_instance_details_file(compartment_id):
    """Create a file with details of instances in the specified compartment.

    Args:
        compartment_id (str): The compartment ID.
    """
    list_instances_response = compute_client.list_instances(compartment_id=compartment_id)
    for instance in list_instances_response.data:
        if instance.shape == "VM.Standard.A1.Flex":
            details = [f"Instance ID: {instance.id}",
                       f"Display Name: {instance.display_name}",
                       f"Availability Domain: {instance.availability_domain}",
                       f"Shape: {instance.shape}",
                       f"State: {instance.lifecycle_state}",
                       "\n"]
            write_into_file('INSTANCE_CREATED', '\n'.join(details))


def handle_errors(command, data, log):
    """Handles errors and logs messages.

    Args:
        command (str): The OCI command being executed.
        data (dict): The data or error information returned from the OCI service.
        log (logging.Logger): The logger instance for logging messages.

    Raises:
        Exception: Raises an exception if an unexpected error occurs.
    """
    log.info("Command: %s\nOutput: %s", command, data)
    if "code" in data:
        if data["code"] == "TooManyRequests" or data["message"] == "Out of host capacity.":
            time.sleep(WAIT_TIME)
            return True
    raise Exception("Error: %s" % data)


def execute_oci_command(client, method, *args, **kwargs):
    """Executes an OCI command using the specified OCI client.

    Args:
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
    """Generates an SSH key pair and saves them to the specified files.

    Args:
        public_key_file (str): The file to save the public key.
        private_key_file (str): The file to save the private key.
    """
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(private_key_file)
    # Save public key to file
    write_into_file(public_key_file, f"ssh-rsa {key.get_base64()} {Path(public_key_file).stem}_auto_generated")


def read_or_generate_ssh_public_key(public_key_file):
    """Reads the SSH public key from the file if it exists, else generates and reads it.

    Args:
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
    """Launches an OCI Compute instance using the specified parameters.

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
    if not OCI_IMAGE_ID:
        images = execute_oci_command(
            compute_client,
            "list_images",
            compartment_id=oci_tenancy,
            shape="VM.Standard.A1.Flex",
        )
        shortened_images = [{key: json.loads(str(image))[key] for key in IMAGE_LIST_KEYS} for image in images]
        write_into_file('images_list.json', json.dumps(shortened_images, indent=2))
        oci_image_id = next(image.id for image in images if
                            image.operating_system == OPERATING_SYSTEM and image.operating_system_version == OS_VERSION)
        logging.info("OCI_IMAGE_ID: %s", oci_image_id)
    else:
        oci_image_id = OCI_IMAGE_ID

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
                    boot_volume_size_in_gbs=BOOT_VOL_SIZE,
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
