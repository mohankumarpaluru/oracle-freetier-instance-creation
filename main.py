import time
import sys
import logging
import signal
from app.config import config
from app.notifications import notifications
from app.oci_client import oci_client

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)
log = logging.getLogger("main")

def signal_handler(sig, frame):
    log.info("🛑 Received termination signal. Shutting down gracefully...")
    notifications.send_message("🛑 The OCI Instance Creation Script has been stopped manually.")
    sys.exit(0)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    notifications.send_message("🚀 OCI Instance Creation Script: Starting up!")

    try:
        while True:
            try:
                success = oci_client.launch_instance()
                if success:
                    log.info("Instance created successfully! Exiting.")
                    break
                
                log.info(f"Instance not created. Retrying in {config.WAIT_TIME} seconds...")
                time.sleep(config.WAIT_TIME)

            except Exception as e:
                # If launch_instance raises a non-retryable exception, it's caught here
                # Retryable exceptions are logged and return False inside launch_instance
                log.error(f"Critical error in main loop: {e}")
                # We might want to exit on critical errors or keep retrying depending on strategy
                # For now, let's wait longer and retry, or exit if it's fatal (which oci_client handles via raise)
                time.sleep(config.WAIT_TIME)
                
    except Exception as e:
        log.critical(f"Unhandled exception: {e}")
        notifications.notify_failure(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
