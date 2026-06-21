from __future__ import annotations
import unittest
from latka_jazn.core.neuropsychology_map import NeuropsychologyMapper

class TestNeuropsychologyMap(unittest.TestCase):
    def test_memory_and_emotion_select_principles(self):
        keys = [p.source_key for p in NeuropsychologyMapper().principles_for_text("pamięć emocje tożsamość")]
        self.assertIn("pmc_interacting_brain_systems_memory_consolidation", keys)
        self.assertIn("pmc_hippocampus_prefrontal_amygdala_learning_memory", keys)

if __name__ == "__main__":
    unittest.main()
