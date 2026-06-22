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

    def copy_source_controlled_canon(self, root: Path) -> None:
        packaged_root = Path(__file__).resolve().parents[1]
        src = packaged_root / "latka_jazn" / "resources" / "canon" / "LATKA_IDENTITY_CANON.json"
        dst = root / "latka_jazn" / "resources" / "canon" / "LATKA_IDENTITY_CANON.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    def test_bootstrap_returns_latka_not_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.copy_source_controlled_canon(root)
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
            self.copy_source_controlled_canon(root)
            engine = self.engine(root)
            try:
                out = engine.handle_user_message("🫸🐾")
            finally:
                engine.shutdown()
        self.assertIn("🐾🫷", out)


if __name__ == "__main__":
    unittest.main()
