"""Tests for evals/freeze_fixture.py. All data here is synthetic."""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from consent_engine.models.vendor import Vendor
from consent_engine.tools.tool_02_violation_classifier import is_google_acm_vendor
from consent_engine.tools.tool_05_vendor_library import lookup_vendor

REPO_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "freeze_fixture", REPO_ROOT / "evals" / "freeze_fixture.py"
)
assert _spec and _spec.loader
ff = importlib.util.module_from_spec(_spec)
sys.modules["freeze_fixture"] = ff
_spec.loader.exec_module(ff)

S3 = "s3_fresh_load_optout_preset"
INCONCLUSIVE = "s3_inconclusive_unknown_cmp"


def _request(url: str, *, ts: str = "2026-06-01T00:00:00Z", status: int | None = 200) -> dict:
    return {
        "url": url,
        "method": "GET",
        "timestamp": ts,
        "status_code": status,
        "request_type": "script",
        "initiator": None,
    }


def _document(status: int | None = 200) -> dict:
    return {**_request("https://site.test/", status=status), "request_type": "document"}


def _finding(name: str = "Acme Ads", domains: tuple[str, ...] = ("acme-ads.test",)) -> dict:
    return {
        "vendor": {"name": name, "domains": list(domains)},
        "status": "confirmed_violation",
        "methodology": S3,
        "cookies_observed": ["_acme"],
        "gcs_value": None,
        "gpc_honored": None,
        "evidence": [],
        "notes": "",
    }


def _audit(findings: list[dict] | None = None, **overrides: object) -> dict:
    return {
        "audit_id": "a1",
        "url": "https://site.test/",
        "timestamp": "2026-06-01T00:00:00Z",
        "methodology": S3,
        "cmp_interaction_method": "cookie_injection",
        "detected_cmp": "OneTrust",
        "gcd_raw": None,
        "gpc_tested": False,
        "findings": findings or [],
        "pixel_firings": [],
        **overrides,
    }


def _write_audit(path: Path, audit: dict, requests: list[dict]) -> Path:
    path.mkdir(parents=True)
    (path / "audit_result.json").write_text(json.dumps(audit))
    (path / "evidence.jsonl").write_text("".join(json.dumps(r) + "\n" for r in requests))
    return path


def test_request_ids_are_stable_across_runs():
    records = [_request("https://a.test/1"), _request("https://a.test/2")]
    first = [r["request_id"] for r in ff.assign_request_ids(records)]
    second = [r["request_id"] for r in ff.assign_request_ids(records)]
    assert first == second


def test_identical_requests_get_distinct_ids():
    records = [_request("https://a.test/1"), _request("https://a.test/1")]
    ids = [r["request_id"] for r in ff.assign_request_ids(records)]
    assert len(set(ids)) == 2


def test_document_without_status_is_a_failed_scan():
    assert ff.classify_scan_outcome(_audit(), [_document(status=None)]) == "failed"


def test_redirect_only_scan_is_failed():
    assert ff.classify_scan_outcome(_audit(), [_document(status=302)]) == "failed"


def test_two_request_static_site_is_not_failed():
    assert ff.classify_scan_outcome(_audit(), [_document(), _document()]) == "complete"


def test_failed_banner_click_is_partial_even_with_zero_findings():
    audit = _audit(cmp_interaction_method="banner_click_failed")
    assert ff.classify_scan_outcome(audit, [_document()]) == "partial"


def test_inconclusive_methodology_is_partial():
    assert ff.classify_scan_outcome(_audit(methodology=INCONCLUSIVE), [_document()]) == "partial"


def test_finding_links_to_requests_on_vendor_subdomain():
    requests = ff.assign_request_ids(
        [_request("https://px.acme-ads.test/c"), _request("https://other.test/")]
    )
    link = ff.link_finding(_finding(), requests, [])
    assert link == {
        "linked_request_ids": [requests[0]["request_id"]],
        "link_status": "request_linked",
    }


def test_lookalike_host_does_not_link():
    requests = ff.assign_request_ids([_request("https://notacme-ads.test/c")])
    link = ff.link_finding(_finding(), requests, [])
    assert link["linked_request_ids"] == []


def test_finding_links_through_pixel_firing_url():
    requests = ff.assign_request_ids([_request("https://cdn.elsewhere.test/p")])
    pixels = [{"vendor_name": "Acme Ads", "url": "https://cdn.elsewhere.test/p"}]
    link = ff.link_finding(_finding(), requests, pixels)
    assert link["linked_request_ids"] == [requests[0]["request_id"]]


def test_vendor_with_domains_and_no_request_is_no_match():
    link = ff.link_finding(_finding(), [], [])
    assert link == {"linked_request_ids": [], "link_status": "no_match"}


def test_vendor_without_domains_is_not_checked():
    requests = ff.assign_request_ids([_request("https://px.acme-ads.test/c")])
    link = ff.link_finding(_finding(domains=()), requests, [])
    assert link == {"linked_request_ids": [], "link_status": "not_checked"}


def test_pixel_missing_from_evidence_is_reported_unresolved():
    requests = ff.assign_request_ids([_request("https://a.test/1")])
    pixels = [{"vendor_name": "Acme Ads", "url": "https://gone.test/p"}]
    assert ff.unresolved_pixels(pixels, requests) == [
        {"vendor_name": "Acme Ads", "url": "https://gone.test/p"}
    ]


def _meta_finding(methodology: str) -> dict:
    vendor = lookup_vendor("_fbp")
    assert vendor is not None
    return {
        **_finding(),
        "vendor": vendor.model_dump(mode="json"),
        "methodology": methodology,
        "cookies_observed": ["_fbp"],
    }


def test_confirmed_finding_is_downgraded_under_todays_engine_when_inconclusive():
    finding = _meta_finding(INCONCLUSIVE)
    assert ff.status_today(finding, [finding], None) == "requires_further_investigation"


def test_label_selection_keeps_rare_statuses_under_the_cap():
    findings = [
        {"finding_id": f"f{i}", "engine_status": "confirmed_violation"} for i in range(5)
    ] + [{"finding_id": "rare", "engine_status": "acm_cookieless_ping"}]
    chosen = ff.select_for_labels(findings, cap=2)
    assert len(chosen) == 2
    assert "rare" in [f["finding_id"] for f in chosen]


@pytest.fixture
def frozen(tmp_path: Path) -> Path:
    requests = [_document(), _request("https://px.acme-ads.test/c")]
    source = _write_audit(tmp_path / "src", _audit([_finding()]), requests)
    return ff.freeze_audit(source, tmp_path / "fixtures" / "fx-01", "fx-01")


def test_frozen_fixture_passes_check(frozen: Path):
    assert ff.check_fixture(frozen) == []


def test_manifest_records_outcome_and_counts(frozen: Path):
    manifest = json.loads((frozen / "manifest.json").read_text())
    assert manifest["scan_outcome"] == "complete"
    assert manifest["request_count"] == 2
    assert manifest["finding_count"] == 1


def test_check_catches_citation_to_unknown_request(frozen: Path):
    path = frozen / "findings.jsonl"
    finding = json.loads(path.read_text())
    finding["linked_request_ids"] = ["req_doesnotexist"]
    path.write_text(json.dumps(finding) + "\n")
    assert any("req_doesnotexist" in error for error in ff.check_fixture(frozen))


def test_label_sheet_leaves_kenneths_columns_blank(frozen: Path):
    sheet = frozen.parent / "labels.csv"
    ff.write_label_sheet(frozen.parent, sheet, cap=10)
    rows = list(csv.DictReader(sheet.open()))
    assert len(rows) == 1
    assert {rows[0][column] for column in ff.HUMAN_COLUMNS} == {""}


def test_label_sheet_refuses_to_overwrite_existing_labels(frozen: Path):
    sheet = frozen.parent / "labels.csv"
    sheet.write_text("hand labels")
    with pytest.raises(FileExistsError):
        ff.write_label_sheet(frozen.parent, sheet, cap=10)
    assert sheet.read_text() == "hand labels"


def test_fixtures_directory_is_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", "evals/fixtures/fx-01/manifest.json"],
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0


def test_blocked_main_document_with_healthy_iframe_is_failed():
    iframe = {**_request("https://frame.test/"), "request_type": "document"}
    assert ff.classify_scan_outcome(_audit(), [_document(status=403), iframe]) == "failed"


def test_redirect_then_success_is_not_failed():
    final = {**_request("https://www.site.test/"), "request_type": "document"}
    assert ff.classify_scan_outcome(_audit(), [_document(status=301), final]) == "complete"


def test_stealthy_scan_is_partial():
    audit = _audit(scan_mode_used="stealthy")
    assert ff.classify_scan_outcome(audit, [_document()]) == "partial"


def test_only_requests_after_the_reload_are_in_the_final_load():
    records = [
        _document(),
        _request("https://first.test/"),
        _document(),
        _request("https://b.test/"),
    ]
    flags = [r["citable"] for r in ff.mark_final_load(ff.assign_request_ids(records))]
    assert flags == [False, False, True, True]


def test_first_load_request_is_not_cited():
    records = [_document(), _request("https://px.acme-ads.test/c"), _document()]
    requests = ff.mark_final_load(ff.assign_request_ids(records))
    assert ff.link_finding(_finding(), requests, [])["link_status"] == "no_match"


def test_banner_click_scan_has_no_saved_evidence():
    assert ff.evidence_saved(_audit(cmp_interaction_method="banner_click_failed")) is False


def test_injection_and_ccpa_scans_have_saved_evidence():
    assert ff.evidence_saved(_audit(cmp_interaction_method="cookie_injection")) is True
    assert ff.evidence_saved(_audit(cmp_interaction_method="ccpa_optout")) is True


def test_finding_from_unsaved_session_cites_nothing(tmp_path: Path):
    audit = _audit([_finding()], cmp_interaction_method="banner_click_failed")
    source = _write_audit(
        tmp_path / "src", audit, [_document(), _request("https://px.acme-ads.test/c")]
    )
    fixture = ff.freeze_audit(source, tmp_path / "fx", "fx")
    finding = json.loads((fixture / "findings.jsonl").read_text())
    assert finding["linked_request_ids"] == []
    assert finding["link_status"] == "evidence_unavailable"


def test_google_finding_under_denied_gcs_cannot_be_rechecked():
    vendor = {"name": "Google Analytics", "domains": [], "category": "analytics"}
    assert is_google_acm_vendor(Vendor.model_validate(vendor))
    finding = {
        **_finding(),
        "vendor": vendor,
        "gcs_value": {"raw": "G100", "ad_storage": "denied", "analytics_storage": "denied"},
    }
    assert ff.status_today(finding, [finding], None) is None


def test_request_domains_link_a_vendor_the_library_leaves_blank():
    requests = ff.assign_request_ids([_request("https://www.google-analytics.com/g/collect")])
    finding = _finding(name="Google Analytics", domains=())
    link = ff.link_finding(finding, requests, [])
    assert link["linked_request_ids"] == [requests[0]["request_id"]]


def test_vendor_with_only_a_template_domain_is_not_checked():
    finding = _finding(domains=("ads-[account].acme-ads.test",))
    assert ff.link_finding(finding, [], [])["link_status"] == "not_checked"


def test_complete_log_is_fully_citable_and_saved(tmp_path: Path):
    audit = _audit(
        [_finding()], cmp_interaction_method="banner_click_failed", evidence_log_complete=True
    )
    requests = [_request("https://px.acme-ads.test/c"), _document(), _document()]
    source = _write_audit(tmp_path / "src", audit, requests)
    fixture = ff.freeze_audit(source, tmp_path / "fx", "fx")
    finding = json.loads((fixture / "findings.jsonl").read_text())
    assert finding["link_status"] == "request_linked"


def test_request_before_the_decline_reload_is_not_cited(tmp_path: Path):
    audit = _audit([_finding()], cmp_interaction_method="banner_click", evidence_log_complete=True)
    requests = [_document(), _request("https://px.acme-ads.test/c"), _document()]
    source = _write_audit(tmp_path / "src", audit, requests)
    fixture = ff.freeze_audit(source, tmp_path / "fx", "fx")
    finding = json.loads((fixture / "findings.jsonl").read_text())
    assert finding["link_status"] == "no_match"


@pytest.mark.parametrize(
    ("vendor", "url"),
    [
        ("Cloudflare", "https://cdnjs.cloudflare.com/ajax/libs/x.js"),
        ("Shopify", "https://cdn.shopify.com/s/files/x.js"),
    ],
)
def test_static_cdn_request_is_not_a_citation(vendor: str, url: str):
    requests = ff.assign_request_ids([_request(url)])
    finding = _finding(name=vendor, domains=("shopify.com",))
    assert ff.link_finding(finding, requests, [])["linked_request_ids"] == []
