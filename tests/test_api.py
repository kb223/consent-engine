"""Tests for src/consent_engine/api.py — the FastAPI surface.

Verifies the v0.5.0 security model:

- POST /audit returns 503 when CONSENT_ENGINE_API_TOKEN is unset (closed
  default; the unauthenticated default that shipped in v0.1.x–v0.4.x is
  intentionally broken in v0.5.0).
- POST /audit returns 401 when a request omits the token or sends a wrong one.
- POST /audit succeeds with a valid Bearer token (run_audit is mocked so the
  test doesn't launch Playwright).
- GET /healthz returns 200 + the version.

The actual run_audit pipeline is exercised end-to-end in the smoke test
documented at docs/release-v0.5.0/e2e-smoke-test.md — these tests focus on
the HTTP surface contract.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from consent_engine import __version__
from consent_engine.api import app


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts without the audit-token env var set."""
    monkeypatch.delenv("CONSENT_ENGINE_API_TOKEN", raising=False)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ----------------------------------------------------------------------
# /healthz
# ----------------------------------------------------------------------


def test_healthz_returns_ok(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


# ----------------------------------------------------------------------
# POST /audit — token gate
# ----------------------------------------------------------------------


def test_audit_returns_503_when_token_env_unset(client: TestClient) -> None:
    """Unauthenticated default is intentionally broken — operators must set a token."""
    resp = client.post("/audit", json={"url": "https://example.com"})
    assert resp.status_code == 503
    assert "CONSENT_ENGINE_API_TOKEN" in resp.json()["detail"]


def test_audit_returns_401_when_token_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONSENT_ENGINE_API_TOKEN", "sentinel-token-1234")
    resp = client.post("/audit", json={"url": "https://example.com"})
    assert resp.status_code == 401


def test_audit_returns_401_when_token_wrong(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONSENT_ENGINE_API_TOKEN", "sentinel-token-1234")
    resp = client.post(
        "/audit",
        json={"url": "https://example.com"},
        headers={"Authorization": "Bearer wrong-value"},
    )
    assert resp.status_code == 401


def test_audit_accepts_bearer_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Mock the audit pipeline so the test stays fast + doesn't need Playwright."""
    monkeypatch.setenv("CONSENT_ENGINE_API_TOKEN", "good-token")
    monkeypatch.chdir(tmp_path)

    fake_bundle = _make_fake_bundle()
    with patch(
        "consent_engine.audit.run_audit", new=AsyncMock(return_value=fake_bundle)
    ):
        resp = client.post(
            "/audit",
            json={"url": "https://example.com"},
            headers={"Authorization": "Bearer good-token"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"] == fake_bundle.audit_id
    assert body["bundle"].endswith(fake_bundle.audit_id)


def test_audit_accepts_x_token_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """The X-Consent-Engine-Token header is an accepted alternative to Authorization."""
    monkeypatch.setenv("CONSENT_ENGINE_API_TOKEN", "good-token")
    monkeypatch.chdir(tmp_path)

    fake_bundle = _make_fake_bundle()
    with patch(
        "consent_engine.audit.run_audit", new=AsyncMock(return_value=fake_bundle)
    ):
        resp = client.post(
            "/audit",
            json={"url": "https://example.com"},
            headers={"X-Consent-Engine-Token": "good-token"},
        )
    assert resp.status_code == 200


# ----------------------------------------------------------------------
# Test fixtures
# ----------------------------------------------------------------------


def _make_fake_bundle():
    """Build a minimal AuditBundle for HTTP-surface tests (no Playwright run)."""
    from datetime import UTC, datetime

    from consent_engine.audit import AuditBundle
    from consent_engine.models.audit_request import ConsentState
    from consent_engine.models.audit_result import (
        AuditResult,
        GTMExtractionMethod,
        MethodologyFlag,
    )
    from consent_engine.models.scan_result import ScanResult

    now = datetime.now(UTC)
    scan = ScanResult(
        url="https://example.com",
        methodology=MethodologyFlag.S3,
        consent_state=ConsentState.OPTED_OUT,
        timestamp=now,
        cookies=[],
        network_requests=["https://example.com/"],
        request_log=[],
        gtm_extraction_method=GTMExtractionMethod.NONE,
    )
    result = AuditResult(
        audit_id="test-fake-12345678-1234-1234-1234-123456789abc",
        url="https://example.com",
        timestamp=now,
        methodology=MethodologyFlag.S3,
        findings=[],
        detected_jurisdiction="US",
    )
    return AuditBundle(
        audit_id=result.audit_id,
        audit_result=result,
        scan_result=scan,
        report_html="<html></html>",
        executive_summary="Test summary.",
        deck_marp_md="# test",
    )
