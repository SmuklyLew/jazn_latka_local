from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine

class TestMemoryStore(unittest.TestCase):
    def test_memory_stats_present(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            packaged_root = Path(__file__).resolve().parents[1]
            (root / "memory" / "raw").mkdir(parents=True)
            (root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json").write_text(
                (packaged_root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            engine = JaznEngine(JaznConfig(network_time_first=False, root=root))
            try:
                stats = engine.store.stats()
            finally:
                engine.shutdown()
        self.assertIn("events", stats)
        self.assertIn("source_files", stats)
        self.assertIn("legacy_conversations", stats)

if __name__ == "__main__":
    unittest.main()
