from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from time import perf_counter
from typing import Any
import email.utils
import json, os, re, urllib.request

from .timestamp_policy import (
    TIMESTAMP_LOCAL_FALLBACK_ALLOWED_DEFAULT,
    TIMESTAMP_MAX_AGE_SECONDS,
    TIMESTAMP_NETWORK_FIRST_DEFAULT,
    TIMESTAMP_NETWORK_TIMEOUT_SECONDS,
    timestamp_runtime_policy,
)

POLISH_WEEKDAYS = {
    0: "poniedziałek", 1: "wtorek", 2: "środa", 3: "czwartek",
    4: "piątek", 5: "sobota", 6: "niedziela"
}

@dataclass(slots=True)
class TimeSample:
    dt: datetime
    source: str
    trusted: bool
    error: str | None = None


@dataclass(slots=True)
class NetworkTimeCheckResult:
    status: str
    source: str | None = None
    datetime_iso: str | None = None
    error: str | None = None
    elapsed_ms: int = 0
    timeout_seconds: float = 1.5
    urls_tried: list[str] = field(default_factory=list)
    does_not_block_startup: bool = True
    time_trust_state: str = "unknown_time_source"
    fallback_sample: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _last_sunday_utc(year: int, month: int) -> datetime:
    """Return the last Sunday of a month at 01:00 UTC.

    This is used only for the emergency Europe/Warsaw fallback when the
    platform has no IANA timezone database and the optional tzdata package is
    not installed. It is not a replacement for ZoneInfo/tzdata.
    """
    candidate = datetime(year, month, 31, 1, 0, 0, tzinfo=timezone.utc)
    while candidate.weekday() != 6:  # Sunday
        candidate -= timedelta(days=1)
    return candidate


def _fallback_warsaw_timezone(now_utc: datetime | None = None) -> timezone:
    """Best-effort fixed-offset fallback for current Europe/Warsaw time.

    The correct path is ZoneInfo("Europe/Warsaw") backed by system tzdata or
    the Python tzdata package. On Windows this data may be missing. In that
    case we prefer a clearly degraded fixed-offset fallback over crashing at
    startup. The fallback uses the modern EU DST boundaries for the current
    date, but it does not provide full historical/future IANA rules.
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    start_dst = _last_sunday_utc(now_utc.year, 3)
    end_dst = _last_sunday_utc(now_utc.year, 10)
    offset_hours = 2 if start_dst <= now_utc < end_dst else 1
    return timezone(
        timedelta(hours=offset_hours),
        name=f"Europe/Warsaw-fallback-fixed-UTC+{offset_hours:02d}",
    )


def resolve_timezone(timezone_name: str = "Europe/Warsaw"):
    """Return an IANA timezone or a controlled fallback instead of crashing startup."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name == "Europe/Warsaw":
            return _fallback_warsaw_timezone()
        return timezone.utc


class WarsawClock:
    def __init__(self, timezone_name: str = "Europe/Warsaw") -> None:
        self.timezone_name = timezone_name
        self.degraded = False
        self.degraded_reason: str | None = None
        try:
            self.tz = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            self.tz = resolve_timezone(timezone_name)
            self.degraded = True
            self.degraded_reason = (
                f"ZoneInfo timezone '{timezone_name}' is not available. "
                "Install tzdata with: py -m pip install tzdata. "
                "Using a degraded Europe/Warsaw fixed-offset fallback for startup; "
                "this is not a full IANA timezone database."
            )
        self.last_sample: TimeSample | None = None

    def now(
        self,
        network_first: bool = TIMESTAMP_NETWORK_FIRST_DEFAULT,
        *,
        allow_fallback: bool = TIMESTAMP_LOCAL_FALLBACK_ALLOWED_DEFAULT,
        timeout_seconds: float = TIMESTAMP_NETWORK_TIMEOUT_SECONDS,
    ) -> TimeSample:
        injected = self._injected_trusted_time()
        if injected:
            self.last_sample = injected
            return injected
        if network_first:
            sample = self._network_time(timeout_seconds=timeout_seconds)
            if sample:
                self.last_sample = sample
                return sample
            if not allow_fallback:
                sample = TimeSample(
                    datetime.now(self.tz),
                    "network_time_unavailable_no_fallback",
                    False,
                    error="network time unavailable and local fallback disabled",
                )
                self.last_sample = sample
                return sample
        sample = self._local_time_sample()
        self.last_sample = sample
        return sample

    def network_time_check(self, *, timeout_seconds: float = 1.5) -> dict[str, Any]:
        started = perf_counter()
        urls_tried: list[str] = []
        try:
            injected = self._injected_trusted_time()
            if injected:
                elapsed_ms = int((perf_counter() - started) * 1000)
                return NetworkTimeCheckResult(
                    status="ok",
                    source=injected.source,
                    datetime_iso=injected.dt.isoformat(),
                    elapsed_ms=elapsed_ms,
                    timeout_seconds=timeout_seconds,
                    urls_tried=[injected.source],
                    does_not_block_startup=True,
                    time_trust_state="trusted_time",
                ).to_dict()
            sample = self._network_time(timeout_seconds=timeout_seconds, urls_tried=urls_tried)
            elapsed_ms = int((perf_counter() - started) * 1000)
            if sample is None:
                fallback = self._local_time_sample()
                return NetworkTimeCheckResult(
                    status="unavailable",
                    error="network time unavailable; using explicit local machine fallback; this does not block runtime startup",
                    elapsed_ms=elapsed_ms,
                    timeout_seconds=timeout_seconds,
                    urls_tried=urls_tried,
                    does_not_block_startup=True,
                    time_trust_state="network_time_unavailable_local_machine_unverified",
                    fallback_sample={
                        "source": fallback.source,
                        "trusted": fallback.trusted,
                        "datetime_iso": fallback.dt.isoformat(),
                        "error": fallback.error,
                    },
                ).to_dict()
            return NetworkTimeCheckResult(
                status="ok",
                source=sample.source,
                datetime_iso=sample.dt.isoformat(),
                elapsed_ms=elapsed_ms,
                timeout_seconds=timeout_seconds,
                urls_tried=urls_tried,
                does_not_block_startup=True,
                time_trust_state="trusted_time",
            ).to_dict()
        except Exception as exc:
            elapsed_ms = int((perf_counter() - started) * 1000)
            return NetworkTimeCheckResult(
                status="error",
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=elapsed_ms,
                timeout_seconds=timeout_seconds,
                urls_tried=urls_tried,
                does_not_block_startup=True,
                time_trust_state="network_time_check_error_local_machine_available",
                fallback_sample={
                    "source": self._local_time_sample().source,
                    "trusted": False,
                    "datetime_iso": self._local_time_sample().dt.isoformat(),
                    "error": f"{type(exc).__name__}: {exc}",
                },
            ).to_dict()

    def _network_time(self, *, timeout_seconds: float = 1.5, urls_tried: list[str] | None = None) -> TimeSample | None:
        json_urls = [
            "https://worldtimeapi.org/api/timezone/Europe/Warsaw",
            "https://timeapi.io/api/TimeZone/zone?timeZone=Europe/Warsaw",
        ]
        headers = {"Cache-Control": "no-cache", "Pragma": "no-cache", "User-Agent": "LatkaJazn/14.8.5"}
        for url in json_urls:
            if urls_tried is not None:
                urls_tried.append(url)
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout_seconds) as r:
                    date_header = r.headers.get("Date")
                    body = r.read().decode("utf-8", errors="replace")
                data = json.loads(body)
                raw = data.get("datetime") or data.get("currentLocalTime") or data.get("dateTime")
                if raw:
                    raw = raw.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(raw)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=self.tz)
                    return TimeSample(dt.astimezone(self.tz), url, True)
                if date_header:
                    parsed = email.utils.parsedate_to_datetime(date_header)
                    return TimeSample(parsed.astimezone(self.tz), url + "#http-date", True)
            except Exception:
                continue

        # Fallback sieciowy oparty o nagłówek Date ze strony, której treść zwykle
        # jest dostępna nawet wtedy, gdy API czasu ma limit lub awarię.
        for url in [
            "https://www.timeanddate.com/worldclock/poland/warsaw",
            "https://www.google.com/generate_204",
            "https://api.github.com",
            "https://www.cloudflare.com/cdn-cgi/trace",
            "https://www.microsoft.com",
            "https://www.openai.com",
        ]:
            if urls_tried is not None:
                urls_tried.append(url)
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout_seconds) as r:
                    date_header = r.headers.get("Date")
                    html = r.read(250_000).decode("utf-8", errors="replace")
                if url.startswith("https://www.timeanddate.com"):
                    m = re.search(r'id="ct"[^>]*>([^<]+)<', html)
                    # Treść strony nie zawsze zawiera pełną datę w prostym formacie, więc
                    # nagłówek HTTP Date pozostaje bezpieczniejszym źródłem.
                if date_header:
                    parsed = email.utils.parsedate_to_datetime(date_header)
                    return TimeSample(parsed.astimezone(self.tz), url + "#http-date", True)
            except Exception:
                continue
        return None

    def _injected_trusted_time(self) -> TimeSample | None:
        raw = os.environ.get("JAZN_TRUSTED_TIME_ISO", "").strip()
        if not raw:
            return None
        source = os.environ.get("JAZN_TRUSTED_TIME_SOURCE", "chatgpt_loader_time").strip() or "chatgpt_loader_time"
        max_age_seconds = self._injected_time_max_age_seconds() or TIMESTAMP_MAX_AGE_SECONDS
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            freshness_seconds = abs(int((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()))
            if freshness_seconds > max_age_seconds:
                return None
            return TimeSample(dt.astimezone(self.tz), source, True)
        except Exception:
            return None

    def _injected_time_max_age_seconds(self) -> int | None:
        raw = os.environ.get("JAZN_TRUSTED_TIME_MAX_AGE_SECONDS", "").strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            return None
        return value if value > 0 else None

    @staticmethod
    def _source_is_injected_trusted_time(source: str | None) -> bool:
        value = str(source or "").strip().lower()
        return value.startswith((
            "chatgpt_web_time_tool",
            "chatgpt_loader_time",
            "openai_web_time_tool",
            "external_trusted_time",
            "injected_trusted_time",
        ))

    def _local_time_sample(self) -> TimeSample:
        return TimeSample(datetime.now(self.tz), "local_fallback", False)

    def header(self, sample: TimeSample | None = None, *, network_first: bool = TIMESTAMP_NETWORK_FIRST_DEFAULT) -> str:
        # P0 timestamp: gdy nie przekazano próbki, header sam próbuje czasu sieciowego.
        # Lokalny fallback pozostaje jawnie nieufny w TimeSample.trusted/source.
        sample = sample or self.now(network_first=network_first)
        dt = sample.dt.astimezone(self.tz)
        offset_seconds = int(dt.utcoffset().total_seconds()) if dt.utcoffset() else 0
        offset_hours = offset_seconds // 3600
        sign = "+" if offset_hours >= 0 else ""
        return f"[🕒 {dt:%Y-%m-%d %H:%M:%S} GMT{sign}{offset_hours}, {POLISH_WEEKDAYS[dt.weekday()]}, Europe/Warsaw]"
    def sample_contract(self, sample: TimeSample | None = None) -> dict[str, Any]:
        sample = sample or self.last_sample or self.now(network_first=TIMESTAMP_NETWORK_FIRST_DEFAULT)
        policy = timestamp_runtime_policy()
        injected_max_age = self._injected_time_max_age_seconds()
        if injected_max_age is not None and self._source_is_injected_trusted_time(sample.source):
            # Keep injected-time freshness validation consistent with the clock acceptance policy.
            policy["max_age_seconds"] = injected_max_age
        return {
            **policy,
            "timestamp_header": self.header(sample),
            "sample_iso": sample.dt.isoformat(),
            "source": sample.source,
            "trusted": sample.trusted,
            "error": sample.error,
        }
