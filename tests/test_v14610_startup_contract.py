from pathlib import Path
from latka_jazn.config import JaznConfig
from latka_jazn.core.startup_contract import build_startup_status, build_startup_summary
ROOT = Path(__file__).resolve().parents[1]

def test_startup_status_has_v14610_fields():
    status = build_startup_status(JaznConfig(root=ROOT)).to_dict()
    assert status['runtime_version'].startswith(('v14.6.10', 'v14.7.0', 'v14.7.1', 'v14.8.0', 'v14.8.1', 'v14.8.2.4', 'v14.8.3'))
    assert 'update_history_status' in status
    assert 'network_policy_status' in status
    assert 'dictionary_provider_status' in status
    assert 'manifest_profile_status' in status
    assert status['raw_memory_status']['chat_html_present'] is False
    assert 'chat_html_archive_present' in status['raw_memory_status']


def test_v14831_startup_status_fast_has_existing_contract_fields():
    status = build_startup_status(JaznConfig(root=ROOT), mode="fast").to_dict()
    assert status.get("startup_status_mode") in {"fast", "metadata"}
    assert status.get("sqlite_health_mode") == "metadata"
    assert "truth_boundary" in status


def test_v14831_startup_summary_is_lightweight():
    summary = build_startup_summary(JaznConfig(root=ROOT))
    assert summary["startup_status_mode"] == "fast"
    assert summary["network_time_used"] is False
    assert summary["sqlite_health_mode"] == "metadata"
