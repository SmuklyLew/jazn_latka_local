# LATKA v14.8.5.014 - bezpieczne odblokowanie po probie aplikacji patcha
# Uruchamiaj linia po linii w PowerShell. Nie rob git push przed weryfikacja.

cd D:\.AI\jazn_latka_local

# 1) Zobacz aktualny stan.
git status --short
git log --oneline -5
git rev-parse --abbrev-ref HEAD
Get-Content .\VERSION.txt -TotalCount 5

# 2) Jesli ostatni commit to lokalny "baseline v14.8.5.011" z samymi patchami/raportami,
# cofnij tylko commit, ale zostaw pliki na dysku.
git reset --mixed HEAD~1

# 3) Przenies patch 014 poza repo albo zostaw go w repo jako plik roboczy, ale NIE commituj jeszcze.
# Patch 013 masz u siebie w sciezce patchs/upto15.8.6+ po ostatnim commicie/reset.
Test-Path '.\patchs\upto15.8.6+\v14_8_5_013_combined_timestamp_daemon_chat_openai.patch'
Test-Path '.\v14_8_5_014_strict_runtime_truth_fast_continuity_openai_state_gateway.patch'
Test-Path '.\v14_8_5_014_combined_from_v14_8_5_011_to_strict_runtime_truth.patch'

# 4) UWAGA: obecne repo nie jest baza v14.8.5.011, wiec nie aplikuj tutaj v014 inkrementalnego.
# Jesli chcesz pracowac na ZIP v14.8.5.011, zrob nowy folder testowy i rozpakuj tam ZIP.

cd D:\.AI
New-Item -ItemType Directory -Force -Path .\jazn_latka_v14_8_5_014_test | Out-Null
Write-Host 'Rozpakuj ZIP v14.8.5.011 do: D:\.AI\jazn_latka_v14_8_5_014_test'
Write-Host 'Potem skopiuj tam patch combined: v14_8_5_014_combined_from_v14_8_5_011_to_strict_runtime_truth.patch'

# 5) Po rozpakowaniu ZIP v14.8.5.011 i skopiowaniu patcha combined:
# cd D:\.AI\jazn_latka_v14_8_5_014_test
# git init
# git add .
# git commit -m "baseline v14.8.5.011"
# git apply --check .\v14_8_5_014_combined_from_v14_8_5_011_to_strict_runtime_truth.patch
# git apply .\v14_8_5_014_combined_from_v14_8_5_011_to_strict_runtime_truth.patch
# python -m compileall main.py latka_jazn tests
# python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py tests/test_v1485013_chat_command_bridge_contract.py tests/test_v1485014_strict_runtime_truth_gate.py tests/test_v1485014_fast_continuity_and_gateway.py -q
