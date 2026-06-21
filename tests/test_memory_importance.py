from __future__ import annotations
import unittest
from latka_jazn.core.memory_importance import MemoryImportanceAssessor

class TestMemoryImportance(unittest.TestCase):
    def test_identity_memory_is_canonical(self):
        result = MemoryImportanceAssessor().assess("Tożsamość Łatki i ciągłość pamięci są ważne")
        self.assertGreaterEqual(result.importance, 0.7)
        self.assertEqual(result.canonical_impact, 1)

if __name__ == "__main__":
    unittest.main()
