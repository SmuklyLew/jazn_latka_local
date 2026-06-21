from __future__ import annotations
import unittest
from latka_jazn.core.self_architecture import SelfArchitecture

class TestSelfArchitecture(unittest.TestCase):
    def test_all_required_layers_exist(self):
        keys = {x["key"] for x in SelfArchitecture().layers()}
        for key in {
            "identity_core", "episodic_memory", "semantic_memory", "procedural_memory",
            "reflection_journal", "time_model", "uncertainty_model", "boundary_model", "source_library"
        }:
            self.assertIn(key, keys)

    def test_contract_contains_truth_rule(self):
        self.assertIn("pięknej narracji", SelfArchitecture().startup_contract().lower())

if __name__ == "__main__":
    unittest.main()
