from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from latka_jazn.memory.store import MemoryStore
from latka_jazn.memory.layered_memory import LayeredMemory

class TestLayeredMemory(unittest.TestCase):
    def test_episode_and_reflection_are_stored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = MemoryStore(root / "runtime" / "test.sqlite3")
            try:
                lm = LayeredMemory(store, root)
                ep = lm.record_episode(scene="Krzysztof pyta o tożsamość i pamięć", emotional_anchor="ciągłość", source="test")
                lm.reflect_on_episode(ep, meaning_for_latka="To wzmacnia ciągłość", identity_impact="rdzeń", boundary_note="nie zmyślać")
                stats = store.stats()
                self.assertEqual(stats["episodic_memories"], 1)
                self.assertEqual(stats["reflection_entries"], 1)
                found = lm.search_episodes("tożsamość")
                self.assertEqual(len(found), 1)
            finally:
                store.close()

if __name__ == "__main__":
    unittest.main()
