import tempfile
import unittest
from pathlib import Path

from scripts.validate_phase_4_1 import scan_secret_files


FINNHUB_VAR = "FINNHUB_API" + "_KEY"
MARKET_DATA_VAR = "MARKET_DATA_API" + "_KEY"


class Phase41ValidatorSecretScanTests(unittest.TestCase):
    def scan(self, root: Path):
        return scan_secret_files([root], root)

    def test_backend_env_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(f"{FINNHUB_VAR}=real-looking-local-key-1234567890\n")

            issues = self.scan(root)

            self.assertEqual(issues, [])

    def test_env_example_placeholder_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text(f"{FINNHUB_VAR}=\n{MARKET_DATA_VAR}=<real key>\n")

            issues = self.scan(root)

            self.assertEqual(issues, [])

    def test_env_example_real_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text(f"{FINNHUB_VAR}=real-looking-example-key-1234567890\n")

            issues = self.scan(root)

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].path, ".env.example")
            self.assertEqual(issues[0].variable, "FINNHUB_API_KEY")
            self.assertIn("non-placeholder", issues[0].reason)

    def test_source_code_real_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app_dir = root / "app"
            app_dir.mkdir()
            (app_dir / "settings.py").write_text(f'{FINNHUB_VAR}="real-looking-source-key-1234567890"\n')

            issues = self.scan(root)

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].path, "app/settings.py")
            self.assertEqual(issues[0].variable, "FINNHUB_API_KEY")
            self.assertIn("assigned non-placeholder", issues[0].reason)


if __name__ == "__main__":
    unittest.main()
