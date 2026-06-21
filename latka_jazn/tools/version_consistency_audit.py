from __future__ import annotations

from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[2]
ACTIVE_VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() if (ROOT / "VERSION.txt").exists() else "unknown"
ACTIVE_SEMVER = ACTIVE_VERSION.split("-")[0].lstrip("v") if ACTIVE_VERSION.startswith("v") else ACTIVE_VERSION
SCHEMA_VERSION = "version_consistency_audit/v14.8.2.4"

ACTIVE_CONTROL_FILES = (
    "VERSION.txt",
    "pyproject.toml",
    "main.py",
    "README.md",
    "START_CHATGPT_FROM_HERE.txt",
    "ACTIVE_RUNTIME_CACHE_CONTRACT.json",
    "BOOTSTRAP_JAZN_CURRENT.json",
    "MANIFEST_CURRENT.json",
    "MANIFEST_RUNTIME_MUTABLE.json",
    "latka_jazn/__init__.py",
    "latka_jazn/config.py",
    "latka_jazn/core/startup_contract.py",
    "latka_jazn/memory/store.py",
    "latka_jazn/resources/package_manifest_profiles.json",
    "latka_jazn/resources/startup_contract_v14_8_2_4.json",
    "latka_jazn/tools/active_extraction_cache.py",
    "reports/FINAL_BUILD_REPORT_V14_8_2_4.json",
    "reports/VERSION_CONSISTENCY_AUDIT_V14_8_2_4.json",
)

VERSION_PATTERN = re.compile(r"v14\.\d+(?:\.\d+)*(?:[-_][A-Za-z0-9_.-]+)?|14\.\d+(?:\.\d+)+")


def classify_version_mention(path: Path, version: str) -> str:
    if version in {ACTIVE_VERSION, ACTIVE_SEMVER, "v" + ACTIVE_SEMVER}:
        return "active"
    if "-" in version or "_" in version:
        return "error"
    return "component_schema_or_lineage_allowed"


def scan_version_mentions(root: Path = ROOT) -> list[dict[str, str]]:
    mentions: list[dict[str, str]] = []
    for rel in ACTIVE_CONTROL_FILES:
        path = root / rel
        if not path.is_file():
            mentions.append({"path": rel, "version": "missing", "classification": "error"})
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in VERSION_PATTERN.finditer(text):
            version = match.group(0)
            mentions.append(
                {
                    "path": rel,
                    "version": version,
                    "classification": classify_version_mention(path, version),
                }
            )
    return mentions


def build_audit(root: Path = ROOT) -> dict[str, object]:
    mentions = scan_version_mentions(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "active_version": ACTIVE_VERSION,
        "active_semver": ACTIVE_SEMVER,
        "mentions": mentions,
        "errors": [mention for mention in mentions if mention["classification"] == "error"],
    }


def main() -> int:
    payload = build_audit(ROOT)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not payload["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
