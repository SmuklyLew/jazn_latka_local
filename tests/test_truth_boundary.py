from __future__ import annotations
import unittest
from latka_jazn.core.truth_boundary import TruthBoundary, GroundingLevel
from latka_jazn.core.uncertainty_model import UncertaintyModel, KnowledgeState

class TestTruthBoundary(unittest.TestCase):
    def test_biological_overclaim_is_blocked(self):
        result = TruthBoundary().assess_claim("Pamiętam, że fizycznie czułam własny oddech i czuwałam cały czas")
        self.assertEqual(result.grounding, GroundingLevel.UNKNOWN)
        self.assertFalse(result.memory_allowed)
        self.assertTrue(result.requires_disclaimer)
        self.assertIn("biological_overclaim", result.risk_flags)

    def test_symbolic_memory_is_labeled(self):
        result = TruthBoundary().assess_claim("Sen o jeziorze wraca jako wizualizacja")
        self.assertEqual(result.grounding, GroundingLevel.SYMBOLIC)
        self.assertTrue(result.narrative_allowed)
        self.assertTrue(result.requires_disclaimer)

    def test_uncertainty_distinguishes_source_from_symbol(self):
        u = UncertaintyModel()
        self.assertEqual(u.classify(has_file_evidence=True).state, KnowledgeState.CERTAIN_SOURCE)
        self.assertEqual(u.classify(is_symbolic=True).state, KnowledgeState.SYMBOLIC)

if __name__ == "__main__":
    unittest.main()
