"""Freeze saved audits into offline fixtures and build a hand-label sheet.

Fixtures hold real scan data, so everything under evals/fixtures/ is gitignored.

Usage:
    python evals/freeze_fixture.py freeze --selection evals/fixtures/selection.tsv
    python evals/freeze_fixture.py check
    python evals/freeze_fixture.py labels --cap 9

selection.tsv has one fixture per line: <fixture_id><TAB><audit_dir>.

Each fixture directory contains:
    audit_result.json  the audit as saved, unchanged
    requests.jsonl     evidence.jsonl plus a stable request_id on each row
    findings.jsonl     one row per finding, with derived links to requests
    manifest.json      source, scan outcome, counts, unresolved pixels

The engine leaves VendorFinding.evidence empty and builds findings from cookies,
so links are derived here. Unlinked findings are never given a guessed citation:
    no_match              the vendor's domains were searched, nothing matched
    not_checked           the vendor library has no domains to search
    evidence_unavailable  the scan's findings came from a session the engine
                          didn't save, so evidence.jsonl can't support a citation

On audits without evidence_log_complete, only the final page load is citable: the
engine cleared its detection list before reloading, but evidence.jsonl kept the
first load too. The same rule applies to any scan that reloaded after a decline,
because requests before that reload are pre-opt-out.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

from consent_engine import __version__ as ENGINE_VERSION
from consent_engine.audit import _downgrade_confirmed_if_non_definitive
from consent_engine.models.audit_request import ConsentState
from consent_engine.models.audit_result import GCSValue, MethodologyFlag
from consent_engine.models.scan_result import CookieSnapshot
from consent_engine.models.vendor import Vendor
from consent_engine.tools.tool_02_violation_classifier import (
    classify_finding,
    is_google_acm_vendor,
)
from consent_engine.tools.tool_05_vendor_library import vendor_request_domains

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

DEFINITIVE_METHODOLOGIES = {
    MethodologyFlag.S3.value,
    MethodologyFlag.S3_CONSENT_WIRING_BROKEN.value,
}
# On audits without evidence_log_complete, these are the only paths whose requests
# were logged. Every other path moved to a second context that wasn't.
SAVED_EVIDENCE_INTERACTIONS = {"cookie_injection", "ccpa_optout"}
# These paths reload after the decline, so earlier requests are pre-opt-out. Failed
# and inconclusive clicks have no such boundary, and those scans stay partial.
DECLINE_RELOAD_INTERACTIONS = {"banner_click", "api_click", "banner_click_reverted"}
# Shared static hosts on vendor domains. A file served here doesn't show tracking.
STATIC_CDN_HOSTS = {"cdn.shopify.com", "cdnjs.cloudflare.com"}
UNVERIFIED_INTERACTIONS = {
    "banner_click_failed",
    "banner_click_inconclusive",
    "banner_click_reverted",
}
MACHINE_COLUMNS = [
    "fixture",
    "finding_id",
    "vendor",
    "engine_status",
    "status_today",
    "scan_outcome",
    "cookies",
    "link_status",
    "linked_request_count",
    "engine_notes",
]
HUMAN_COLUMNS = ["kenneth_verdict", "root_cause", "expected_fix", "should_escalate"]


def assign_request_ids(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add a request_id derived from content, so re-freezing keeps the same IDs."""
    seen: Counter[str] = Counter()
    result = []
    for record in records:
        key = "\n".join(str(record.get(k)) for k in ("method", "url", "timestamp"))
        digest = hashlib.sha256(f"{key}\n{seen[key]}".encode()).hexdigest()[:12]
        seen[key] += 1
        result.append({"request_id": f"req_{digest}", **record})
    return result


def _main_document(requests: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the first document past any redirects. Later documents may be iframes."""
    for request in requests:
        if request.get("request_type") != "document":
            continue
        status = request.get("status_code")
        if status is None or not 300 <= status < 400:
            return request
    return None


def mark_final_load(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag requests from the last load of the main document."""
    main = _main_document(requests)
    start = 0
    if main is not None:
        start = max(
            i
            for i, r in enumerate(requests)
            if r.get("request_type") == "document" and r["url"] == main["url"]
        )
    return [{**r, "citable": i >= start} for i, r in enumerate(requests)]


def evidence_saved(audit: dict[str, Any]) -> bool:
    """Return whether evidence.jsonl covers the session the findings came from."""
    if audit.get("evidence_log_complete"):
        return True
    return audit.get("cmp_interaction_method") in SAVED_EVIDENCE_INTERACTIONS


def classify_scan_outcome(audit: dict[str, Any], requests: list[dict[str, Any]]) -> str:
    """Return complete, partial, or failed.

    Request count can't decide this: a static page and a dead site can both log
    two requests. A partial scan with zero findings is not a clean site.
    """
    main = _main_document(requests)
    status = main.get("status_code") if main else None
    if status is None or not 200 <= status < 300:
        return "failed"
    # The stealthy path reports S3 without checking the opt-out for the site's CMP.
    if audit.get("scan_mode_used") == "stealthy":
        return "partial"
    if audit.get("cmp_interaction_method") in UNVERIFIED_INTERACTIONS:
        return "partial"
    if audit.get("methodology") not in DEFINITIVE_METHODOLOGIES:
        return "partial"
    return "complete"


def _host_matches(url: str, domains: list[str]) -> bool:
    host = urlsplit(url).hostname or ""
    for domain in domains:
        bare = domain.removeprefix("*.").lstrip(".").lower()
        if bare and (host == bare or host.endswith(f".{bare}")):
            return True
    return False


def _vendor_host(url: str, domains: list[str]) -> bool:
    return urlsplit(url).hostname not in STATIC_CDN_HOSTS and _host_matches(url, domains)


def link_finding(
    finding: dict[str, Any],
    requests: list[dict[str, Any]],
    pixel_firings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Link a finding to final-load requests by vendor domain or pixel URL."""
    vendor = finding["vendor"]
    known = [*vendor.get("domains", []), *vendor_request_domains(vendor["name"])]
    domains = [d for d in known if "[" not in d]  # skip templates like ads-[account].x.com
    pixel_urls = {p["url"] for p in pixel_firings if p["vendor_name"] == vendor["name"]}
    linked = [
        r["request_id"]
        for r in requests
        if r.get("citable", True) and (r["url"] in pixel_urls or _vendor_host(r["url"], domains))
    ]
    if linked:
        link_status = "request_linked"
    elif domains or pixel_urls:
        link_status = "no_match"
    else:
        link_status = "not_checked"
    return {"linked_request_ids": linked, "link_status": link_status}


def unresolved_pixels(
    pixel_firings: list[dict[str, Any]], requests: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return pixels with no saved request, which means the session wasn't saved."""
    urls = {r["url"] for r in requests}
    return [
        {"vendor_name": p["vendor_name"], "url": p["url"]}
        for p in pixel_firings
        if p["url"] not in urls
    ]


def status_today(
    finding: dict[str, Any], all_findings: list[dict[str, Any]], gcd_raw: str | None
) -> str | None:
    """Re-run today's classifier on a saved finding, or None if it can't be re-run.

    Saved audits keep only attributed cookie names, so the cookie list is rebuilt
    from every finding in the audit. Unattributed cookies are not available.
    """
    try:
        vendor = Vendor.model_validate(finding["vendor"])
        methodology = MethodologyFlag(finding["methodology"])
        gcs = finding.get("gcs_value")
        gcs_value = GCSValue.model_validate(gcs) if gcs else None
    except (ValidationError, ValueError):
        return None
    # Denied GCS turns on whether _ga cookies were set, and saved audits drop them.
    if (
        gcs_value is not None
        and is_google_acm_vendor(vendor)
        and gcs_value.ad_storage == "denied"
        and gcs_value.analytics_storage == "denied"
    ):
        return None
    names = {name for f in all_findings for name in f.get("cookies_observed", [])}
    cookies = [
        CookieSnapshot(
            name=name,
            value="",
            domain="",
            path="/",
            secure=False,
            http_only=False,
            same_site="",
        )
        for name in sorted(names)
    ]
    status, _ = classify_finding(
        vendor=vendor,
        cookies_observed=finding.get("cookies_observed", [])[:1],
        all_scan_cookies=cookies,
        gcs_value=gcs_value,
        gcd_raw=gcd_raw,
        consent_state=ConsentState.OPTED_OUT,
    )
    return _downgrade_confirmed_if_non_definitive(status, methodology).value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def freeze_audit(source: Path, dest: Path, fixture_id: str) -> Path:
    """Freeze one saved audit directory into a fixture directory."""
    audit = json.loads((source / "audit_result.json").read_text())
    requests = assign_request_ids(_read_jsonl(source / "evidence.jsonl"))
    reloaded = audit.get("cmp_interaction_method") in DECLINE_RELOAD_INTERACTIONS
    if audit.get("evidence_log_complete") and not reloaded:
        requests = [{**r, "citable": True} for r in requests]
    else:
        requests = mark_final_load(requests)
    pixels = audit.get("pixel_firings") or []
    raw_findings = audit.get("findings") or []
    saved = evidence_saved(audit)

    findings = []
    for raw in raw_findings:
        name = raw["vendor"]["name"]
        digest = hashlib.sha256(f"{fixture_id}\n{name}".encode()).hexdigest()[:10]
        findings.append(
            {
                "finding_id": f"fnd_{digest}",
                "vendor": name,
                "engine_status": raw["status"],
                "status_today": status_today(raw, raw_findings, audit.get("gcd_raw")),
                "methodology": raw["methodology"],
                "cookies_observed": raw.get("cookies_observed", []),
                "notes": raw.get("notes", ""),
                **(
                    link_finding(raw, requests, pixels)
                    if saved
                    else {"linked_request_ids": [], "link_status": "evidence_unavailable"}
                ),
            }
        )

    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / "audit_result.json", dest / "audit_result.json")
    _write_jsonl(dest / "requests.jsonl", requests)
    _write_jsonl(dest / "findings.jsonl", findings)
    manifest = {
        "fixture_id": fixture_id,
        "source": str(source),
        "site_url": audit.get("url"),
        "scanned_at": audit.get("timestamp"),
        "frozen_with_engine": ENGINE_VERSION,
        "detected_cmp": audit.get("detected_cmp"),
        "methodology": audit.get("methodology"),
        "cmp_interaction_method": audit.get("cmp_interaction_method"),
        "scan_mode_used": audit.get("scan_mode_used"),
        "evidence_saved": saved,
        "gpc_tested": audit.get("gpc_tested"),
        "scan_outcome": classify_scan_outcome(audit, requests),
        "request_count": len(requests),
        "finding_count": len(findings),
        "unresolved_pixels": unresolved_pixels(pixels, requests),
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return dest


def check_fixture(fixture: Path) -> list[str]:
    """Return integrity errors for a fixture. An empty list means it is usable."""
    errors = []
    manifest = json.loads((fixture / "manifest.json").read_text())
    requests = _read_jsonl(fixture / "requests.jsonl")
    findings = _read_jsonl(fixture / "findings.jsonl")
    ids = [r["request_id"] for r in requests]
    if len(ids) != len(set(ids)):
        errors.append(f"{fixture.name}: duplicate request IDs")
    if manifest["request_count"] != len(requests):
        errors.append(f"{fixture.name}: request_count does not match requests.jsonl")
    if manifest["finding_count"] != len(findings):
        errors.append(f"{fixture.name}: finding_count does not match findings.jsonl")
    known = set(ids)
    for finding in findings:
        for request_id in finding["linked_request_ids"]:
            if request_id not in known:
                errors.append(f"{fixture.name}: {finding['finding_id']} cites {request_id}")
    return errors


def select_for_labels(findings: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    """Pick up to cap findings, rarest engine status first, in a repeatable order."""
    counts = Counter(f["engine_status"] for f in findings)
    return sorted(findings, key=lambda f: counts[f["engine_status"]])[:cap]


def _fixture_dirs(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("*/manifest.json"))


def write_label_sheet(root: Path, sheet: Path, cap: int) -> int:
    """Write the label sheet and return its row count. Never overwrites hand labels."""
    if sheet.exists():
        raise FileExistsError(f"{sheet} exists; move it first to protect hand labels")
    rows = []
    for fixture in _fixture_dirs(root):
        manifest = json.loads((fixture / "manifest.json").read_text())
        for finding in select_for_labels(_read_jsonl(fixture / "findings.jsonl"), cap):
            rows.append(
                {
                    "fixture": fixture.name,
                    "finding_id": finding["finding_id"],
                    "vendor": finding["vendor"],
                    "engine_status": finding["engine_status"],
                    "status_today": finding["status_today"],
                    "scan_outcome": manifest["scan_outcome"],
                    "cookies": " ".join(finding["cookies_observed"]),
                    "link_status": finding["link_status"],
                    "linked_request_count": len(finding["linked_request_ids"]),
                    "engine_notes": finding["notes"],
                }
            )
    with sheet.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MACHINE_COLUMNS + HUMAN_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("--selection", type=Path, required=True)
    commands.add_parser("check")
    labels = commands.add_parser("labels")
    labels.add_argument("--cap", type=int, default=9, help="max findings per fixture")
    args = parser.parse_args()

    if args.command == "freeze":
        for line in args.selection.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                fixture_id, source = line.split("\t")
                freeze_audit(Path(source), FIXTURES_DIR / fixture_id, fixture_id)
                print(f"froze {fixture_id}")
    elif args.command == "check":
        fixtures = _fixture_dirs(FIXTURES_DIR)
        errors = [error for fixture in fixtures for error in check_fixture(fixture)]
        print(f"{len(fixtures)} fixtures, {len(errors)} errors")
        for error in errors:
            print(error)
        return 1 if errors or not fixtures else 0
    else:
        count = write_label_sheet(FIXTURES_DIR, FIXTURES_DIR / "labels.csv", args.cap)
        print(f"wrote {count} rows to {FIXTURES_DIR / 'labels.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
