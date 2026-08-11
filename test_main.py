import importlib.util
import logging
import os
from pathlib import Path
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch


PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PATH = PROJECT_ROOT / "main.py"
MODULE_NAME = "main_under_test"


class FakeServiceError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class FakeOciModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeConfigParser:
    def read(self, _path):
        return []

    def get(self, _section, _option):
        return "test-user"

    def sections(self):
        return []

    def items(self, _section):
        return []


def load_main_without_oci_setup():
    """Import main after replacing OCI/config construction with local fakes."""
    fake_oci = types.ModuleType("oci")
    fake_oci.config = SimpleNamespace(from_file=Mock(return_value={}))
    fake_oci.identity = SimpleNamespace(IdentityClient=Mock(return_value=Mock()))
    fake_oci.core = SimpleNamespace(
        VirtualNetworkClient=Mock(return_value=Mock()),
        ComputeClient=Mock(return_value=Mock()),
        models=SimpleNamespace(
            LaunchInstanceShapeConfigDetails=FakeOciModel,
            LaunchInstanceDetails=FakeOciModel,
            CreateVnicDetails=FakeOciModel,
            LaunchInstanceAvailabilityConfigDetails=FakeOciModel,
            InstanceOptions=FakeOciModel,
            InstanceSourceViaImageDetails=FakeOciModel,
        ),
    )
    fake_oci.exceptions = SimpleNamespace(ServiceError=FakeServiceError)

    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = Mock()
    fake_paramiko = types.ModuleType("paramiko")
    fake_paramiko.RSAKey = SimpleNamespace(generate=Mock())
    fake_requests = types.ModuleType("requests")
    fake_requests.RequestException = Exception
    fake_requests.post = Mock()

    environment = {
        "OCI_CONFIG": "test-config",
        "OCT_FREE_AD": "AD-1",
        "DISPLAY_NAME": "test-instance",
        "REQUEST_WAIT_TIME_SECS": "60",
        "SSH_AUTHORIZED_KEYS_FILE": "test-key.pub",
        "OCI_IMAGE_ID": "test-image",
        "OCI_COMPUTE_SHAPE": "VM.Standard.A1.Flex",
        "OCI_SUBNET_ID": "test-subnet",
        "BOOT_VOLUME_SIZE": "50",
    }
    fake_modules = {
        "oci": fake_oci,
        "dotenv": fake_dotenv,
        "paramiko": fake_paramiko,
        "requests": fake_requests,
    }

    sys.modules.pop(MODULE_NAME, None)
    with patch.dict(os.environ, environment, clear=False), \
            patch.dict(sys.modules, fake_modules), \
            patch("configparser.ConfigParser", FakeConfigParser), \
            patch("logging.basicConfig"), \
            patch("logging.FileHandler", return_value=logging.NullHandler()):
        spec = importlib.util.spec_from_file_location(MODULE_NAME, MAIN_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[MODULE_NAME] = module
        spec.loader.exec_module(module)

    return module


class MainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = load_main_without_oci_setup()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop(MODULE_NAME, None)

    def test_retry_delay_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "REQUEST_WAIT_TIME_SECS"):
            self.main.validate_retry_delay("0")

        with self.assertRaisesRegex(ValueError, "REQUEST_WAIT_TIME_SECS"):
            self.main.validate_retry_delay("not-a-number")

        self.assertEqual(self.main.validate_retry_delay("15"), 15)

    def test_boot_volume_size_is_capped_at_free_tier_safe_bound(self):
        with self.assertRaisesRegex(ValueError, "200 GB"):
            self.main.validate_boot_volume_size("201")

        self.assertEqual(self.main.validate_boot_volume_size("50"), 50)
        self.assertEqual(self.main.validate_boot_volume_size("20"), 50)

    def test_arm_success_requires_running_name_and_requested_shape_config(self):
        matching_config = SimpleNamespace(ocpus=2, memory_in_gbs=12)
        cases = (
            ("provisioning", SimpleNamespace(
                shape=self.main.ARM_SHAPE,
                display_name="test-instance",
                lifecycle_state="PROVISIONING",
                shape_config=matching_config,
            ), False),
            ("wrong-name", SimpleNamespace(
                shape=self.main.ARM_SHAPE,
                display_name="another-instance",
                lifecycle_state="RUNNING",
                shape_config=matching_config,
            ), False),
            ("wrong-shape-config", SimpleNamespace(
                shape=self.main.ARM_SHAPE,
                display_name="test-instance",
                lifecycle_state="RUNNING",
                shape_config=SimpleNamespace(ocpus=1, memory_in_gbs=6),
            ), False),
            ("missing-shape-config", SimpleNamespace(
                shape=self.main.ARM_SHAPE,
                display_name="test-instance",
                lifecycle_state="RUNNING",
            ), False),
            ("matching", SimpleNamespace(
                shape=self.main.ARM_SHAPE,
                display_name="test-instance",
                lifecycle_state="RUNNING",
                shape_config=matching_config,
            ), True),
        )

        for name, instance, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(self.main.is_requested_arm_instance(instance), expected)

    def test_state_check_does_not_sleep_after_final_attempt(self):
        self.main.WAIT_TIME = 7
        with patch.object(self.main, "list_all_instances", return_value=[]) as list_instances, \
                patch.object(self.main.time, "sleep") as sleep:
            found = self.main.check_instance_state_and_write(
                "test-compartment", self.main.ARM_SHAPE, tries=3
            )

        self.assertFalse(found)
        self.assertEqual(list_instances.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(7), call(7)])

    def test_limit_exceeded_waits_then_retries_without_generic_error_handler(self):
        self.main.WAIT_TIME = 17
        launch_client = Mock()
        launch_client.launch_instance.side_effect = [
            FakeServiceError(400, "LimitExceeded", "limit reached"),
            SimpleNamespace(status=200),
        ]

        def execute_command(_client, method, *_args, **_kwargs):
            if method == "get_user":
                return SimpleNamespace(compartment_id="test-tenancy")
            if method == "list_availability_domains":
                return [SimpleNamespace(name="test:AD-1")]
            self.fail(f"Unexpected OCI command: {method}")

        logger = Mock()
        with patch.object(self.main, "compute_client", launch_client), \
                patch.object(self.main, "execute_oci_command", side_effect=execute_command), \
                patch.object(self.main, "read_or_generate_ssh_public_key", return_value="ssh-key"), \
                patch.object(self.main, "check_instance_state_and_write",
                             side_effect=[False, False, True]) as check_state, \
                patch.object(self.main, "handle_errors") as handle_errors, \
                patch.object(self.main, "logging_step5", logger), \
                patch.object(self.main.time, "sleep") as sleep:
            self.main.launch_instance()

        self.assertEqual(launch_client.launch_instance.call_count, 2)
        self.assertEqual(check_state.call_args_list, [
            call("test-tenancy", self.main.ARM_SHAPE, tries=1),
            call("test-tenancy", self.main.ARM_SHAPE),
            call("test-tenancy", self.main.ARM_SHAPE),
        ])
        sleep.assert_called_once_with(17)
        handle_errors.assert_not_called()
        log_messages = " ".join(
            call_info.args[0] for call_info in logger.info.call_args_list
        ).lower()
        self.assertNotIn("proceeding", log_messages)


if __name__ == "__main__":
    unittest.main()
