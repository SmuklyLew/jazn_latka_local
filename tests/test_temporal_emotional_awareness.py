from __future__ import annotations
import unittest
from latka_jazn.core.emotion_layers import EmotionalLayerModel
from latka_jazn.core.temporal_awareness import TemporalAwareness

class TestTemporalEmotionalAwareness(unittest.TestCase):
    def test_long_gap_is_classified(self):
        state = TemporalAwareness().classify_gap(21600)
        self.assertEqual(state.category, "powrót_po_długiej_przerwie")

    def test_identity_emotion_layer_exists(self):
        profile = EmotionalLayerModel().appraise("Tożsamość Łatki, pamięć i ciągłość")
        names = [layer.name for layer in profile.layers]
        self.assertIn("rdzeń tożsamości", names)

if __name__ == "__main__":
    unittest.main()
