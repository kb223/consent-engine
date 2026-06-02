"""Regression tests for release-hardening fixes.

Each test pins a defect surfaced by the release validation run (50 real
sites + failure/SSRF probes) so it cannot silently recur:

  F1      methodology enum must never render as raw text in the report
  F-LOGIC under an unrecognised CMP, a CONFIRMED firing downgrades to observed
  F-JUR   operator-identity markers (GmbH / "registered in England" / S.r.l.)
          route generic-TLD sites to EU/UK without flipping plain US sites
  F-ERR   the CLI surfaces a clean one-line error (never a traceback) when an
          audit cannot run (e.g. the SSRF guard rejects an internal host)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from consent_engine.audit import _downgrade_confirmed_if_non_definitive
from consent_engine.models.audit_result import (
    AuditResult,
    MethodologyFlag,
    ViolationStatus,
)
from consent_engine.tools.jurisdiction_detector import detect_jurisdiction
from consent_engine.tools.tool_08_report_generator import generate_report

# ---------------------------------------------------------------------------
# F-JUR — operator-identity signal on generic TLDs
# ---------------------------------------------------------------------------


def test_operator_identity_routes_eu_uk_on_generic_tld() -> None:
    assert detect_jurisdiction(
        "<html><body>Acme Software GmbH, Berlin</body></html>", "https://acme.com"
    ) == "EU"
    assert detect_jurisdiction(
        "<html><body>Foo, registered in England and Wales</body></html>", "https://foo.com"
    ) == "UK"
    assert detect_jurisdiction(
        "<html><body>iubenda S.r.l., Bologna</body></html>", "https://iubenda.io"
    ) == "EU"
    assert detect_jurisdiction(
        "<html><body>Usercentrics GmbH, Handelsregister B 12345</body></html>",
        "https://usercentrics.com",
    ) == "EU"


def test_operator_identity_does_not_flip_plain_us_site() -> None:
    # No EU/UK operator markers -> a generic .com stays US (no false positives).
    assert detect_jurisdiction(
        "<html lang='en-US'><body>Acme Inc., a Delaware LLC, San Francisco</body></html>",
        "https://acme.com",
    ) == "US"


def test_country_tld_still_wins_over_operator_text() -> None:
    assert detect_jurisdiction("<html><body>x</body></html>", "https://x.de") == "EU"
    assert detect_jurisdiction("<html><body>Acme Inc</body></html>", "https://x.co.uk") == "UK"
    assert detect_jurisdiction("<html><body>x</body></html>", "https://x.ca") == "CA"


# ---------------------------------------------------------------------------
# F-LOGIC — confirmed -> observed downgrade under an unrecognised CMP
# ---------------------------------------------------------------------------


def test_confirmed_downgrades_under_inconclusive() -> None:
    assert (
        _downgrade_confirmed_if_non_definitive(
            ViolationStatus.CONFIRMED, MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP
        )
        == ViolationStatus.REQUIRES_INVESTIGATION
    )


def test_confirmed_preserved_only_under_definitive() -> None:
    # Definitive methodologies keep a CONFIRMED finding.
    for m in (MethodologyFlag.S3, MethodologyFlag.S3_CONSENT_WIRING_BROKEN):
        assert (
            _downgrade_confirmed_if_non_definitive(ViolationStatus.CONFIRMED, m)
            == ViolationStatus.CONFIRMED
        )
    # Every NON-definitive methodology downgrades CONFIRMED to observed: both the
    # unrecognised-CMP scan and the no-Google-Consent-Mode case (BBC-type sites),
    # so per-finding badges match the methodology-gated (zero) headline count.
    for m in (
        MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP,
        MethodologyFlag.S3_NO_GOOGLE_CONSENT_MODE,
    ):
        assert (
            _downgrade_confirmed_if_non_definitive(ViolationStatus.CONFIRMED, m)
            == ViolationStatus.REQUIRES_INVESTIGATION
        )


def test_non_confirmed_status_unchanged_under_inconclusive() -> None:
    for s in (
        ViolationStatus.NO_EVIDENCE,
        ViolationStatus.REQUIRES_INVESTIGATION,
        ViolationStatus.ACM_COMPLIANT,
    ):
        assert (
            _downgrade_confirmed_if_non_definitive(s, MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP)
            == s
        )


# ---------------------------------------------------------------------------
# F1 — methodology enum never leaks as raw text into the rendered report
# ---------------------------------------------------------------------------

_PRODUCTION_METHODOLOGIES = (
    MethodologyFlag.S1,
    MethodologyFlag.S3,
    MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP,
    MethodologyFlag.S3_CONSENT_WIRING_BROKEN,
    MethodologyFlag.S3_NO_GOOGLE_CONSENT_MODE,
)


def _audit(methodology: MethodologyFlag) -> AuditResult:
    return AuditResult(
        audit_id="t-0000-0000-0000-000000000000",
        url="https://example.com",
        timestamp=datetime.now(UTC),
        methodology=methodology,
        findings=[],
        detected_jurisdiction="US",
        detected_cmp=None,
        gcs_value=None,
    )


def test_report_never_renders_raw_methodology_enum() -> None:
    for m in _PRODUCTION_METHODOLOGIES:
        html = asyncio.run(
            generate_report(_audit(m), wiki_pages=[], executive_summary="Test.")
        )
        for flag in MethodologyFlag:
            assert flag.value not in html, (
                f"raw methodology enum '{flag.value}' leaked into the report "
                f"when methodology={m.value}"
            )


# ---------------------------------------------------------------------------
# F-ERR — CLI surfaces a clean error, never a traceback, when audit can't run
# ---------------------------------------------------------------------------


def test_cli_audit_clean_error_on_ssrf_reject(capsys) -> None:
    from consent_engine.cli import main

    rc = main(["audit", "http://127.0.0.1/", "--no-open"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "error:" in err.lower()
    assert "Traceback" not in err  # the whole point: no stacktrace leaks to the user


def test_cli_audit_scan_exception_hides_traceback_by_default(capsys, monkeypatch, tmp_path) -> None:
    import consent_engine.audit as audit_mod
    from consent_engine.cli import main

    async def _boom(*args, **kwargs):
        raise RuntimeError("synthetic scan failure")

    monkeypatch.setattr(audit_mod, "run_audit", _boom)
    monkeypatch.delenv("CONSENT_ENGINE_DEBUG", raising=False)

    rc = main(["audit", "https://example.com", "--no-open", "--output-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "synthetic scan failure" in err
    assert "Traceback" not in err


def test_cli_audit_debug_env_prints_traceback(capsys, monkeypatch, tmp_path) -> None:
    import consent_engine.audit as audit_mod
    from consent_engine.cli import main

    async def _boom(*args, **kwargs):
        raise RuntimeError("synthetic scan failure")

    monkeypatch.setattr(audit_mod, "run_audit", _boom)
    monkeypatch.setenv("CONSENT_ENGINE_DEBUG", "1")

    rc = main(["audit", "https://example.com", "--no-open", "--output-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Traceback" in err
    assert "RuntimeError: synthetic scan failure" in err
