from __future__ import annotations

from pathlib import Path

from latka_jazn.nlp_reasoning.adapters.morfeusz_adapter import MorfeuszReasoningAdapter
from latka_jazn.nlp_reasoning.adapters.polimorf_adapter import PolimorfDictionaryAdapter
from latka_jazn.nlp_reasoning.lemma_selector import build_token_morph_analyses
from latka_jazn.nlp_reasoning.morph_tags import parse_morfeusz_tag
from latka_jazn.nlp_reasoning.pipeline import PolishReasoningPipeline


class FakeMorfeusz:
    def analyse(self, text: str):
        assert "Mam" in text
        return [
            (0, 1, ("Mam", "mama", "subst:pl:gen:f")),
            (0, 1, ("Mam", "mamić", "impt:sg:sec:imperf")),
            (0, 1, ("Mam", "mieć", "fin:sg:pri:imperf")),
            (1, 2, ("próbkę", "próbka", "subst:sg:acc:f")),
            (2, 3, (".", ".", "interp")),
        ]


def test_morfeusz_adapter_parses_real_shape_with_features():
    adapter = MorfeuszReasoningAdapter(engine=FakeMorfeusz())
    candidates = adapter.analyse("Mam próbkę.")
    assert adapter.status.available is True
    assert any(c.lemma == "mieć" and c.features["pos"] == "fin" for c in candidates)
    noun = next(c for c in candidates if c.lemma == "próbka")
    assert noun.features["number"] == "sg"
    assert noun.features["case"] == "acc"
    assert noun.features["gender"] == "f"


def test_lemma_selector_prefers_miec_for_mam_when_candidates_are_ambiguous():
    adapter = MorfeuszReasoningAdapter(engine=FakeMorfeusz())
    candidates = adapter.analyse("Mam próbkę.")
    analyses = build_token_morph_analyses(["Mam", "próbkę", "."], candidates)
    selected = analyses[0].selected
    assert selected is not None
    assert selected.lemma == "mieć"
    assert selected.provider == "morfeusz2-sgjp"
    assert selected.candidate_count == 3
    assert "mieć" in selected.reason


def test_polimorf_adapter_reads_external_tsv_without_bundling(tmp_path: Path):
    polimorf = tmp_path / "polimorf.tsv"
    polimorf.write_text("testowe\ttestowy\tadj:pl:nom.acc.voc:n:pos\npróbkę\tpróbka\tsubst:sg:acc:f\n", encoding="utf-8")
    adapter = PolimorfDictionaryAdapter(root=tmp_path, path=polimorf)
    candidates = adapter.analyse_tokens(["Próbkę", "inną"])
    assert adapter.status.available is True
    assert len(candidates) == 1
    assert candidates[0].lemma == "próbka"
    assert candidates[0].provider == "polimorf"
    assert candidates[0].features["case"] == "acc"


def test_pipeline_uses_injected_morfeusz_and_selected_lemmas():
    frame = PolishReasoningPipeline(use_optional_providers=True, morfeusz_engine=FakeMorfeusz()).analyse("Mam próbkę.")
    data = frame.to_dict()
    assert data["schema_version"] == "polish_reasoning_frame/v14.8.4"
    assert data["token_analyses"][0]["selected"]["lemma"] == "mieć"
    assert any(status["provider"] == "morfeusz2-sgjp" and status["available"] for status in data["provider_statuses"])
    assert any(src["source_id"] == "morfeusz2-sgjp" for src in data["sources_used"])


def test_parse_morfeusz_tag_gives_structured_features():
    features = parse_morfeusz_tag("adj:sg:gen.dat.loc:f:pos")
    assert features["pos"] == "adj"
    assert features["number"] == "sg"
    assert features["gender"] == "f"
    assert features["degree"] == "pos"
