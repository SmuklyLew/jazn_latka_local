from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from latka_jazn.memory.version_update_recorder import VersionUpdateRecorder


class TestDziennikVersionUpdate(unittest.TestCase):
    def test_version_update_writes_dziennik_memory_reflection_and_layers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "memory" / "raw").mkdir(parents=True)
            (root / "memory" / "raw" / "dziennik.json").write_text(
                json.dumps({"meta": {"plik": "dziennik_system.json"}, "entries": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            recorder = VersionUpdateRecorder(root=root)
            try:
                result = recorder.record_version_update(
                    version="v-test",
                    title="Test aktualizacji dziennika",
                    summary="Testuję, czy aktualizacja zapisuje dziennik.",
                    modules=["memory/raw/dziennik.json"],
                    experience="To jest doświadczenie systemowe, nie biologiczne.",
                    memories_to_preserve=["pamiętać powód zmiany", "pamiętać emocje"],
                    emotions=["uważność", "ulga"],
                    truth_boundary="Nie udawać biologicznego przeżycia.",
                    tests=["unit"],
                )
            finally:
                recorder.close()

            self.assertTrue(result.appended_update)
            self.assertTrue(result.appended_memory)
            self.assertTrue(result.appended_reflection)
            self.assertIsNotNone(result.layered_episode_id)
            data = json.loads((root / "memory" / "raw" / "dziennik.json").read_text(encoding="utf-8"))
            kinds = [e["typ"] for e in data["entries"]]
            self.assertEqual(kinds, ["aktualizacja_systemu", "wspomnienie", "refleksja"])
            self.assertIn("wspomnienia_do_zachowania", data["entries"][0])
            self.assertIn("emocje_latki", data["entries"][1])
            self.assertEqual(data["meta"]["schema_version"], "v14.5.1-compatible-extended")

    def test_version_update_is_idempotent_for_dziennik_and_layers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "memory" / "raw").mkdir(parents=True)
            (root / "memory" / "raw" / "dziennik.json").write_text(
                json.dumps({"meta": {}, "entries": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            kwargs = dict(
                version="v-test-idem",
                title="Test idempotencji",
                summary="Ten sam wpis nie może się dublować.",
                modules=["memory/raw/dziennik.json"],
                experience="test",
                memories_to_preserve=["test"],
                emotions=["uważność"],
                truth_boundary="test",
            )
            recorder = VersionUpdateRecorder(root=root)
            try:
                first = recorder.record_version_update(**kwargs)
                second = recorder.record_version_update(**kwargs)
            finally:
                recorder.close()
            data = json.loads((root / "memory" / "raw" / "dziennik.json").read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 3)
            self.assertTrue(first.appended_update)
            self.assertFalse(second.appended_update)
            self.assertIsNone(second.layered_episode_id)
            episodic_lines = (root / "memory" / "layered" / "episodic.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(episodic_lines), 1)


if __name__ == "__main__":
    unittest.main()
