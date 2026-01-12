import os
import configparser
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('oci.env')

class Config:
    def __init__(self):
        self._load_env_vars()
        self._validate_config()

    def _load_env_vars(self):
        self.OCI_CONFIG = os.getenv("OCI_CONFIG", "").strip() or os.path.expanduser("~/.oci/config")
        self.OCT_FREE_AD = os.getenv("OCT_FREE_AD", "").strip()
        self.DISPLAY_NAME = os.getenv("DISPLAY_NAME", "").strip()
        self.WAIT_TIME = int(os.getenv("REQUEST_WAIT_TIME_SECS", "60").strip())
        self.SSH_AUTHORIZED_KEYS_FILE = os.getenv("SSH_AUTHORIZED_KEYS_FILE", "").strip()
        self.OCI_IMAGE_ID = os.getenv("OCI_IMAGE_ID", "").strip() or None
        self.OCI_COMPUTE_SHAPE = os.getenv("OCI_COMPUTE_SHAPE", "VM.Standard.A1.Flex").strip()
        self.SECOND_MICRO_INSTANCE = os.getenv("SECOND_MICRO_INSTANCE", 'False').strip().lower() == 'true'
        self.OCI_SUBNET_ID = os.getenv("OCI_SUBNET_ID", "").strip() or None
        self.OPERATING_SYSTEM = os.getenv("OPERATING_SYSTEM", "").strip()
        self.OS_VERSION = os.getenv("OS_VERSION", "").strip()
        self.ASSIGN_PUBLIC_IP = os.getenv("ASSIGN_PUBLIC_IP", "false").strip().lower() in ["true", "1", "y", "yes"]
        self.BOOT_VOLUME_SIZE = int(os.getenv("BOOT_VOLUME_SIZE", "50").strip())
        
        # Notifications
        self.NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", 'False').strip().lower() == 'true'
        self.EMAIL = os.getenv("EMAIL", "").strip()
        self.EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").strip()
        self.DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
        self.TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID", "").strip()

    def _validate_config(self):
        if self.OCI_COMPUTE_SHAPE not in ("VM.Standard.A1.Flex", "VM.Standard.E2.1.Micro"):
            raise ValueError(f"{self.OCI_COMPUTE_SHAPE} is not an acceptable shape")

        # Check for spaces in critical variables
        critical_vars = [
            self.OCI_CONFIG, self.OCT_FREE_AD, str(self.WAIT_TIME),
            self.SSH_AUTHORIZED_KEYS_FILE, self.OCI_IMAGE_ID,
            self.OCI_COMPUTE_SHAPE, str(self.SECOND_MICRO_INSTANCE),
            self.OCI_SUBNET_ID, self.OS_VERSION, str(self.NOTIFY_EMAIL),
            self.EMAIL, self.EMAIL_PASSWORD, self.DISCORD_WEBHOOK,
            self.TELEGRAM_TOKEN, self.TELEGRAM_USER_ID
        ]
        
        if any(isinstance(v, str) and " " in v for v in critical_vars if v):
             raise ValueError("oci.env has spaces in values which is not acceptable")

        # Validate OCI Config file content (basic check)
        config_parser = configparser.ConfigParser()
        try:
            config_parser.read(self.OCI_CONFIG)
            if not config_parser.sections():
                 # It might be empty or invalid path, but let OCI SDK handle deep validation later.
                 # Just checking for spaces in values as per original script logic
                 pass
            
            for section in config_parser.sections():
                for _, value in config_parser.items(section):
                    if ' ' in value:
                        raise ValueError("oci_config has spaces in values which is not acceptable")
            
            # Extract User ID for basic readiness check
            self.OCI_USER_ID = config_parser.get('DEFAULT', 'user', fallback=None)

        except configparser.Error as e:
            raise ValueError(f"Error reading OCI configuration file: {e}")

# Global instance
config = Config()
