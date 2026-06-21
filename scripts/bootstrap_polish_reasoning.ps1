param(
  [switch]$InstallHeavyModels,
  [switch]$SkipStanza,
  [string]$PolimorfPath = ""
)

Write-Host "[Jaźń] Bootstrap Polish Reasoning NLP v14.8.4" -ForegroundColor Cyan
py -m pip install --upgrade pip

Write-Host "[Jaźń] Installing real Morfeusz2/SGJP provider" -ForegroundColor Cyan
py -m pip install "morfeusz2>=1.99.15"

Write-Host "[Jaźń] Installing optional Polish NLP extras" -ForegroundColor Cyan
py -m pip install -e ".[polish-nlp]"

if ($PolimorfPath -ne "") {
  $env:LATKA_POLIMORF_PATH = $PolimorfPath
  Write-Host "[Jaźń] LATKA_POLIMORF_PATH=$env:LATKA_POLIMORF_PATH" -ForegroundColor Green
} else {
  Write-Host "[Jaźń] PoliMorf is not downloaded automatically. Download it after license review and set LATKA_POLIMORF_PATH." -ForegroundColor Yellow
  Write-Host "Example: `$env:LATKA_POLIMORF_PATH='D:\.AI\external_data\polimorf\polimorf.tsv'" -ForegroundColor Yellow
}

Write-Host "[Jaźń] Testing Morfeusz/PoliMorf status" -ForegroundColor Cyan
py main.py --morfeusz-status
py main.py --polimorf-status
py main.py --polish-morphology "Mam próbkę analizy morfologicznej."

Write-Host "[Jaźń] Installing spaCy Polish model pl_core_news_sm (stage v14.8.5+)" -ForegroundColor Cyan
py -m spacy download pl_core_news_sm

if (-not $SkipStanza) {
  Write-Host "[Jaźń] Downloading Stanza Polish pipeline (stage v14.8.5+)" -ForegroundColor Cyan
  py -c "import stanza; stanza.download('pl')"
}

if ($InstallHeavyModels) {
  Write-Host "[Jaźń] Heavy LLM/transformer checkpoints are intentionally not downloaded automatically." -ForegroundColor Yellow
  Write-Host "Choose exact HerBERT/PLLuM/Bielik checkpoints and licenses before download." -ForegroundColor Yellow
}

Write-Host "[Jaźń] Done. Test with: py main.py --polish-reasoning-frame 'Witaj w tej mrocznej nocy.'" -ForegroundColor Green
