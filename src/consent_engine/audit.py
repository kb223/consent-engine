"""End-to-end audit orchestration.

Single entry point for the CLI, the FastAPI service, and the MCP server.

The audit is deterministic by design — every stage below produces a structured
output that downstream stages consume. The LLM is invoked exactly once, for
the executive summary in `generate_executive_summary()`. Everything else is
plain Python.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from consent_engine.models.audit_result import (
    AuditResult,
    HarAnalysis,
    VendorFinding,
)
from consent_engine.models.scan_result import ScanResult
from consent_engine.tools.jurisdiction_detector import detect_jurisdiction
from consent_engine.tools.tool_01_gtm_parser import parse_gtm_container
from consent_engine.tools.tool_02_violation_classifier import classify_finding
from consent_engine.tools.tool_03_browser_scanner import scan_page_fast
from consent_engine.tools.tool_04_har_analyzer import analyze_har
from consent_engine.tools.tool_05_vendor_library import lookup_vendor
from consent_engine.tools.tool_06_ssgtm_detector import detect_ssgtm
from consent_engine.tools.tool_06b_pixel_detector import detect_pixel_firings
from consent_engine.tools.tool_07_rag_retriever import retrieve_context
from consent_engine.tools.tool_08_report_generator import (
    generate_executive_summary,
    generate_marp_slides,
    generate_report,
)


@dataclass
class AuditBundle:
    """Everything the CLI / API / MCP needs in one place after an audit run."""

    audit_id: str
    audit_result: AuditResult
    scan_result: ScanResult           # raw network log + cookies live here
    report_html: str
    executive_summary: str
    deck_marp_md: str


def ensure_chromium_installed() -> None:
    """Download a Chromium build for patchright if one isn't cached yet.

    patchright is a Playwright fork that patches the runtime to hide common
    automation fingerprints (`navigator.webdriver`, plugins, etc). It uses
    the same `ms-playwright` cache directory as upstream Playwright, so an
    existing Playwright Chromium install is reused; otherwise we shell out
    to `python -m patchright install chromium` (idempotent, ~140 MB).
    """
    cache_dir = Path.home() / "Library/Caches/ms-playwright"
    # Heuristic: any chromium folder under the cache means a Chromium build
    # has been downloaded. Cheaper than launching the browser to test.
    if cache_dir.exists() and any(cache_dir.glob("chromium*")):
        return

    print(
        "Chromium not installed. Downloading (~140 MB, one-time)…",
        file=sys.stderr,
        flush=True,
    )
    res = subprocess.run(
        [sys.executable, "-m", "patchright", "install", "chromium"],
        capture_output=False,
        check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(
            "Failed to install Chromium. Run manually:\n"
            "  python -m patchright install chromium"
        )


async def run_audit(url: str, *, jurisdiction: str | None = None) -> AuditBundle:
    """Run a full forensic consent-compliance audit and return an `AuditBundle`.

    Args:
        url: The URL to audit.
        jurisdiction: Optional override (e.g., "EU", "US", "CA"). Auto-detected
            from the page HTML when omitted.

    Returns:
        AuditBundle — structured AuditResult, raw ScanResult (network log +
        cookies), the rendered HTML report, the LLM-written executive summary,
        and the Marp slide deck.
    """
    audit_id = str(uuid.uuid4())

    # 0. First-run setup: download Chromium binaries if they aren't cached.
    ensure_chromium_installed()

    # 1. Scan (S3 forensic methodology — consent pre-set to "reject all").
    scan, _ = await scan_page_fast(url=url, opted_out=True)

    # 2. Per-vendor classification on observed cookies. Deduplicate by vendor
    #    name; accumulate cookies under each finding.
    findings: list[VendorFinding] = []
    seen: set[str] = set()
    for cookie in scan.cookies:
        vendor = lookup_vendor(cookie.name, cookie_domain=cookie.domain) or lookup_vendor(
            cookie.domain.lstrip(".")
        )
        if not vendor:
            continue
        if vendor.name in seen:
            for f in findings:
                if f.vendor.name == vendor.name:
                    f.cookies_observed.append(cookie.name)
            continue
        seen.add(vendor.name)
        status, notes = classify_finding(
            vendor=vendor,
            cookies_observed=[cookie.name],
            all_scan_cookies=scan.cookies,
            gcs_value=scan.gcs_value,
            gcd_raw=scan.gcd_raw,
            consent_state=scan.consent_state,
        )
        findings.append(
            VendorFinding(
                vendor=vendor,
                status=status,
                methodology=scan.methodology,
                cookies_observed=[cookie.name],
                gcs_value=scan.gcs_value,
                notes=notes,
            )
        )

    # 3. sSGTM + pixel-firing detection on the captured network log.
    ssgtm = await detect_ssgtm(scan.network_requests, url)
    pixel_firings = detect_pixel_firings(scan.network_requests)

    # 4. Jurisdiction + GTM parse + HAR analysis (each is independent).
    resolved_jurisdiction = jurisdiction or detect_jurisdiction(scan.page_html or "", url)
    tag_consent_map = parse_gtm_container(
        gtm_container_js=scan.gtm_container_js or "",
        page_html=scan.page_html or "",
    )
    har_analysis = analyze_har(scan.har_path) if scan.har_path else HarAnalysis()

    # 5. Assemble AuditResult.
    audit_result = AuditResult(
        audit_id=audit_id,
        url=url,
        timestamp=scan.timestamp,
        methodology=scan.methodology,
        gtm_extraction_method=scan.gtm_extraction_method,
        gtm_container_id=scan.gtm_container_id,
        ssgtm_detected=ssgtm.detected,
        ssgtm_domain=ssgtm.domain,
        gpc_tested=False,
        gcs_value=scan.gcs_value,
        gcd_raw=scan.gcd_raw,
        findings=findings,
        detected_jurisdiction=resolved_jurisdiction,
        tag_consent_map=tag_consent_map,
        gcs_timeline=har_analysis.gcs_timeline,
        post_payloads=har_analysis.post_payloads,
        consent_api_responses=har_analysis.consent_api_responses,
        pixel_firings=pixel_firings,
        cmp_interaction_method=scan.cmp_interaction_method,
        detected_cmp=scan.detected_cmp,
        cmp_detection_confidence=scan.cmp_detection_confidence,
        bot_detection_encountered=scan.bot_detection_encountered,
        scan_mode_used=scan.scan_mode_used,
    )

    # 6. Wiki context retrieval (markdown KB, no vector DB).
    wiki_pages = await retrieve_context(audit_result)

    # 7. LLM executive summary (the only non-deterministic step).
    exec_summary = await generate_executive_summary(audit_result, wiki_pages)

    # 8. HTML report + Marp slide deck.
    report_html = await generate_report(audit_result, wiki_pages, exec_summary)
    deck_md = generate_marp_slides(audit_result, exec_summary, brand="kjb")

    return AuditBundle(
        audit_id=audit_id,
        audit_result=audit_result,
        scan_result=scan,
        report_html=report_html,
        executive_summary=exec_summary,
        deck_marp_md=deck_md,
    )


def run_audit_sync(url: str, *, jurisdiction: str | None = None) -> AuditBundle:
    """Synchronous wrapper for callers outside an event loop."""
    return asyncio.run(run_audit(url, jurisdiction=jurisdiction))
