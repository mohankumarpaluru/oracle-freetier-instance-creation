import logging
import oci
import json
import time
import sys
from app.config import config
from app.notifications import notifications

class OCIClient:
    def __init__(self):
        self.log = logging.getLogger("oci_client")
        self._init_clients()

    def _init_clients(self):
        try:
            self.oci_config = oci.config.from_file(config.OCI_CONFIG)
            self.iam_client = oci.identity.IdentityClient(self.oci_config)
            self.network_client = oci.core.VirtualNetworkClient(self.oci_config)
            self.compute_client = oci.core.ComputeClient(self.oci_config)
            
            # Get User Tenancy
            user_info = self.iam_client.get_user(config.OCI_USER_ID if hasattr(config, 'OCI_USER_ID') and config.OCI_USER_ID else self.oci_config['user']).data
            self.tenancy_id = user_info.compartment_id
            self.log.info(f"OCI Tenancy ID: {self.tenancy_id}")

        except Exception as e:
            self.log.error(f"Failed to initialize OCI clients: {e}")
            raise

    def get_availability_domain(self):
        ads = self.iam_client.list_availability_domains(compartment_id=self.tenancy_id).data
        target_ads = [ad.name for ad in ads if any(ad.name.endswith(target) for target in config.OCT_FREE_AD.split(","))]
        if not target_ads:
             raise Exception(f"No Availability Domain found matching {config.OCT_FREE_AD}")
        return target_ads[0] # Simplification for now, we can cycle if needed

    def get_subnet_id(self):
        if config.OCI_SUBNET_ID:
            return config.OCI_SUBNET_ID
        
        subnets = self.network_client.list_subnets(compartment_id=self.tenancy_id).data
        if not subnets:
            raise Exception("No subnets found in tenancy.")
        return subnets[0].id

    def get_image_id(self):
        if config.OCI_IMAGE_ID:
            return config.OCI_IMAGE_ID
            
        images = self.compute_client.list_images(
            compartment_id=self.tenancy_id,
            shape=config.OCI_COMPUTE_SHAPE
        ).data
        
        # Save image list for debug/reference
        image_list = [{
            "display_name": img.display_name,
            "id": img.id,
            "operating_system": img.operating_system,
            "operating_system_version": img.operating_system_version
        } for img in images]
        
        with open('images_list.json', 'w') as f:
            json.dump(image_list, f, indent=2)

        try:
            return next(img.id for img in images 
                       if img.operating_system == config.OPERATING_SYSTEM 
                       and img.operating_system_version == config.OS_VERSION)
        except StopIteration:
            raise Exception(f"Image not found for {config.OPERATING_SYSTEM} {config.OS_VERSION}")

    def launch_instance(self):
        ad_name = self.get_availability_domain()
        subnet_id = self.get_subnet_id()
        image_id = self.get_image_id()
        
        logging.info(f"Launching instance in {ad_name}...")

        # Configuration for Test / Micro instances (Commented out for production)
        # shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
        #     ocpus=1, memory_in_gbs=1
        # )

        # Production Configuration for VM.Standard.A1.Flex (Active)
        if config.OCI_COMPUTE_SHAPE == "VM.Standard.A1.Flex":
            shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=4, memory_in_gbs=24
            )
        
        # Read SSH Key
        try:
            with open(config.SSH_AUTHORIZED_KEYS_FILE, 'r') as f:
                ssh_key = f.read()
        except FileNotFoundError:
             # Basic handling if key file is missing, ideally should be generated before
             raise Exception(f"SSH Key file not found at {config.SSH_AUTHORIZED_KEYS_FILE}")

        try:
            launch_details = oci.core.models.LaunchInstanceDetails(
                availability_domain=ad_name,
                compartment_id=self.tenancy_id,
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    assign_public_ip=config.ASSIGN_PUBLIC_IP,
                    assign_private_dns_record=True,
                    display_name=config.DISPLAY_NAME,
                    subnet_id=subnet_id,
                ),
                display_name=config.DISPLAY_NAME,
                shape=config.OCI_COMPUTE_SHAPE,
                availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(
                    recovery_action="RESTORE_INSTANCE"
                ),
                shape_config=shape_config,
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    source_type="image",
                    image_id=image_id,
                    boot_volume_size_in_gbs=config.BOOT_VOLUME_SIZE,
                ),
                metadata={"ssh_authorized_keys": ssh_key},
            )

            response = self.compute_client.launch_instance(launch_instance_details=launch_details)
            
            if response.status == 200:
                self.log.info("Launch request accepted!")
                instance = response.data
                # Build HTML body manually or helper for notification
                html_body = f"Instance {instance.id} created in {ad_name}"
                notifications.notify_success(f"Instance {instance.id} Launched", html_body)
                return True
                
        except oci.exceptions.ServiceError as e:
            if e.code in ("Out of host capacity.", "LimitExceeded", "InternalError"):
                 self.log.warning(f"Temp Error: {e.code} - {e.message}")
                 return False # Retryable
            else:
                self.log.error(f"Fatal Error: {e}")
                notifications.notify_failure(str(e))
                raise

        return False

oci_client = OCIClient()
