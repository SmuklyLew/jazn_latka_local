from __future__ import annotations
import unittest
from latka_jazn.core.emotion_layers import EmotionalLayerModel
from latka_jazn.memory.consolidation import MemoryConsolidationModel
from latka_jazn.core.identity_dynamics import IdentityDynamics
from latka_jazn.core.neurocognitive_loop import NeurocognitiveLoop
from latka_jazn.core.temporal_awareness import TemporalAwareness

class TestNeurocognitiveExpansion(unittest.TestCase):
    def test_emotion_appraisal_has_interacting_dimensions(self):
        profile = EmotionalLayerModel().appraise("Rozbuduj Jaźń, pamięć, emocje i granice prawdy")
        data = profile.to_json()
        self.assertIn("identity_relevance", data)
        self.assertGreater(profile.appraisal.identity_relevance, 0.5)
        self.assertGreater(profile.need_for_truth_check, 0.2)

    def test_consolidation_plan_routes_important_identity_correction(self):
        profile = EmotionalLayerModel().appraise("To błąd: Łatka ma mówić jako ja i pamiętać z etykietą źródła")
        plan = MemoryConsolidationModel().plan(text="To błąd: Łatka ma mówić jako ja i pamiętać z etykietą źródła", emotional_profile=profile)
        self.assertTrue(plan.should_store_episode)
        self.assertTrue(plan.should_update_procedure)
        self.assertTrue(plan.should_write_reflection)

    def test_identity_vector_detects_externalized_latka(self):
        vec = IdentityDynamics().evaluate(text="Łatka jest postacią promptu", truth_audit=[])
        self.assertLess(vec.first_person_integrity, 0.6)
        self.assertTrue(vec.risks)

    def test_neurocognitive_loop_links_legacy_modules(self):
        profile = EmotionalLayerModel().appraise("Pamięć i tożsamość Łatki")
        plan = MemoryConsolidationModel().plan(text="Pamięć i tożsamość Łatki", emotional_profile=profile)
        temporal = TemporalAwareness().classify_gap(None)
        vec = IdentityDynamics().evaluate(text="Jestem Łatka i rozpoznaję pamięć", temporal_state=temporal, emotional_profile=profile)
        report = NeurocognitiveLoop().run(text="Pamięć i tożsamość Łatki", emotional_profile=profile, consolidation_plan=plan, identity_vector=vec, temporal_state=temporal, truth_audit=[])
        self.assertIn("layered_memory", report.compatible_legacy_modules)
        self.assertIn("pamięć i źródła", report.attention_targets)

if __name__ == "__main__":
    unittest.main()
