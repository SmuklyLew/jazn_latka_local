from __future__ import annotations

# P0: jeden punkt prawdy dla widocznego czasu Jaźni.
# Timestamp jest częścią ciągłości i kontraktu prawdy, nie ozdobą UI.

TIMESTAMP_TIMEZONE = "Europe/Warsaw"
TIMESTAMP_NETWORK_FIRST_DEFAULT = True
TIMESTAMP_NETWORK_IN_NORMAL_TURN_DEFAULT = True
TIMESTAMP_LOCAL_FALLBACK_ALLOWED_DEFAULT = True
TIMESTAMP_NETWORK_TIMEOUT_SECONDS = 1.5
TIMESTAMP_MAX_AGE_SECONDS = 120
TIMESTAMP_REQUIRE_TRUSTED_IN_FINAL_VISIBLE = True
TIMESTAMP_POLICY_SCHEMA = "timestamp_runtime_policy/v14.8.5.014-strict"


def timestamp_runtime_policy() -> dict:
    return {
        "schema_version": TIMESTAMP_POLICY_SCHEMA,
        "timezone": TIMESTAMP_TIMEZONE,
        "network_first_default": TIMESTAMP_NETWORK_FIRST_DEFAULT,
        "network_time_in_normal_turn_default": TIMESTAMP_NETWORK_IN_NORMAL_TURN_DEFAULT,
        "local_fallback_allowed_default": TIMESTAMP_LOCAL_FALLBACK_ALLOWED_DEFAULT,
        "network_timeout_seconds": TIMESTAMP_NETWORK_TIMEOUT_SECONDS,
        "max_age_seconds": TIMESTAMP_MAX_AGE_SECONDS,
        "require_trusted_in_final_visible": TIMESTAMP_REQUIRE_TRUSTED_IN_FINAL_VISIBLE,
        "truth_boundary": (
            "Widoczny timestamp ma pochodzić z czasu sieciowego. "
            "Lokalny fallback jest dopuszczalny tylko jako jawnie nieufny tryb awaryjny, "
            "nie jako pełnoprawny aktualny czas internetowy."
        ),
    }
