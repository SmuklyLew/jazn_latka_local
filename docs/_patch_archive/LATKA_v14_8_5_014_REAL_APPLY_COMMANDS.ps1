# v14.8.5.014 REAL combined patch apply commands
# This patch is for a clean v14.8.5.011 tree.
# Run inside the folder where VERSION.txt says exactly: v14.8.5.011

$ErrorActionPreference = "Stop"

Write-Host "== precheck =="
git status --short
git rev-parse --abbrev-ref HEAD
Get-Content .\VERSION.txt -TotalCount 5

Write-Host "== file type check =="
git ls-files -s VERSION.txt main.py latka_jazn/core/clock.py latka_jazn/version.py
Get-Item .\VERSION.txt, .\main.py, .\latka_jazn\core\clock.py, .\latka_jazn\version.py | Format-Table FullName, Mode, Length

Write-Host "== backup branch =="
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
git branch "backup/before-v14.8.5.014-real-$stamp"

Write-Host "== patch check =="
git apply --check .\v14_8_5_014_REAL_combined_from_clean_v14_8_5_011.patch

Write-Host "== patch apply =="
git apply .\v14_8_5_014_REAL_combined_from_clean_v14_8_5_011.patch

Write-Host "== tests =="
python -m compileall main.py latka_jazn tests
python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py tests/test_v1485013_chat_command_bridge_contract.py tests/test_v1485014_strict_runtime_truth_gate.py tests/test_v1485014_fast_continuity_and_gateway.py -q

Write-Host "== after =="
Get-Content .\VERSION.txt -TotalCount 5
git status --short
