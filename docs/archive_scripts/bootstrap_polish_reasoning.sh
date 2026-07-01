#!/usr/bin/env bash
set -euo pipefail

POLIMORF_PATH="${LATKA_POLIMORF_PATH:-}"

echo "[Jaźń] Bootstrap Polish Reasoning NLP v14.8.4"
python -m pip install --upgrade pip

echo "[Jaźń] Installing real Morfeusz2/SGJP provider"
python -m pip install 'morfeusz2>=1.99.15'

echo "[Jaźń] Installing optional Polish NLP extras"
python -m pip install -e '.[polish-nlp]'

if [[ -n "$POLIMORF_PATH" ]]; then
  echo "[Jaźń] LATKA_POLIMORF_PATH=$POLIMORF_PATH"
else
  echo "[Jaźń] PoliMorf is not downloaded automatically. Download it after license review and set LATKA_POLIMORF_PATH."
  echo "Example: export LATKA_POLIMORF_PATH=$HOME/.local/share/latka/polimorf/polimorf.tsv"
fi

echo "[Jaźń] Testing Morfeusz/PoliMorf status"
python main.py --morfeusz-status
python main.py --polimorf-status
python main.py --polish-morphology 'Mam próbkę analizy morfologicznej.'

echo "[Jaźń] Installing spaCy/Stanza Polish resources for next stages (v14.8.5+)"
python -m spacy download pl_core_news_sm
python -c "import stanza; stanza.download('pl')"
echo "[Jaźń] Heavy LLM/transformer checkpoints are not downloaded automatically; pin exact checkpoint and license first."
echo "[Jaźń] Test with: python main.py --polish-reasoning-frame 'Witaj w tej mrocznej nocy.'"
