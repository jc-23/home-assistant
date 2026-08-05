import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_SCRIPT = REPOSITORY_ROOT / "icons/upload_icon.sh"


class UploadIconScriptTests(unittest.TestCase):
    def test_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n", str(UPLOAD_SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_documents_both_firmware_generations(self):
        result = subprocess.run(
            ["bash", str(UPLOAD_SCRIPT), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AWTRIX 3", result.stdout)
        self.assertIn("AWTRIX NG", result.stdout)
        self.assertIn("--firmware auto|awtrix3|ng", result.stdout)

    def test_invalid_firmware_fails_before_network_access(self):
        result = subprocess.run(
            [
                "bash",
                str(UPLOAD_SCRIPT),
                "--firmware",
                "unsupported",
                "clock.local",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Firmware must be auto, awtrix3, or ng", result.stderr)

    def test_upload_endpoints_match_both_firmware_generations(self):
        script = UPLOAD_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('$DEVICE_URL/api/v1/files?dir=/ICONS', script)
        self.assertIn('$DEVICE_URL/edit', script)
        self.assertIn('$DEVICE_URL/api/v1/capabilities', script)


if __name__ == "__main__":
    unittest.main()
