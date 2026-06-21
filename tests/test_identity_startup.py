from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine

class TestIdentityStartup(unittest.TestCase):
    def engine(self, root: Path):
        cfg = JaznConfig(network_time_first=False, root=root)
        return JaznEngine(cfg)

    def test_bootstrap_returns_latka_not_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            packaged_root = Path(__file__).resolve().parents[1]
            (root / "memory" / "raw").mkdir(parents=True)
            (root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json").write_text(
                (packaged_root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            engine = self.engine(root)
            try:
                out = engine.bootstrap()
            finally:
                engine.shutdown()
        self.assertIn("Jestem Łatka", out)
        self.assertNotIn("Łatka jest", out)
        self.assertNotIn("prompt o łatce", out.lower())

    def test_handshake_asymmetry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            packaged_root = Path(__file__).resolve().parents[1]
            (root / "memory" / "raw").mkdir(parents=True)
            (root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json").write_text(
                (packaged_root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            engine = self.engine(root)
            try:
                out = engine.handle_user_message("🫸🐾")
            finally:
                engine.shutdown()
        self.assertIn("🐾🫷", out)

if __name__ == "__main__":
    unittest.main()
