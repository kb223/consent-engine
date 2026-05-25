"""End-to-end audit orchestration.

Single entry point for the CLI, the FastAPI service, and the MCP server.

The audit is deterministic by design — every stage below produces a structured
output that downstream stages consume. The LLM is invoked exactly once, for
the executive summary in `generate_executive_summary()`. Everything else is
plain Python.
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import os
import re
import socket
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from consent_engine.models.audit_result import (
    AuditResult,
    HarAnalysis,
    VendorFinding,
)
from consent_engine.models.scan_result import ScanResult
from consent_engine.tools.cmp_detector import detect_cmp_from_network_only
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

_METADATA_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",        # AWS / GCP / Oracle Cloud IMDSv1
        "fd00:ec2::254",          # AWS IMDSv2 IPv6
        "metadata.google.internal",
        "metadata.azure.com",
        "100.100.100.200",        # Alibaba Cloud
    }
)


def _validate_audit_url(url: str) -> None:
    """SSRF guard. Reject URLs that resolve to private / loopback / metadata IPs.

    Closes the high-severity SSRF surface identified by the v0.5.0 security
    audit: without this, ``consent-engine audit http://169.254.169.254/`` would
    hit cloud metadata services in a real Chromium browser, and the same surface
    is reachable unauthenticated via the FastAPI ``POST /audit`` route.

    Set ``CONSENT_ENGINE_ALLOW_INTERNAL=1`` to bypass (intended for self-hosters
    auditing their own internal staging sites).
    """
    if os.environ.get("CONSENT_ENGINE_ALLOW_INTERNAL") == "1":
        return
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Only http/https URLs allowed; got scheme {parsed.scheme!r}. "
            f"file:// / chrome:// / etc are rejected to prevent local file disclosure."
        )
    host = parsed.hostname
    if host is None:
        raise ValueError(f"URL is missing a hostname: {url!r}")
    if host.lower() in _METADATA_HOSTS:
        raise ValueError(
            f"Refusing to scan known cloud-metadata host: {host}. "
            f"Set CONSENT_ENGINE_ALLOW_INTERNAL=1 to override."
        )
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve hostname {host!r}: {e}") from e
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(
                f"Refusing to scan internal/private IP {addr} (for host {host!r}). "
                f"Set CONSENT_ENGINE_ALLOW_INTERNAL=1 to override."
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
    """Download the Playwright Chromium browser if it isn't on disk yet.

    Playwright ships the browser binaries separately from the Python package,
    so a freshly installed `consent-engine` will hit
    `BrowserType.launch: Executable doesn't exist…` on the first audit.
    This shells out to `playwright install chromium` (idempotent, ~140 MB
    one-time download into ~/Library/Caches/ms-playwright/) so the user
    never has to.
    """
    cache_dir = Path.home() / "Library/Caches/ms-playwright"
    # Heuristic: any chromium folder under the cache means Playwright has
    # downloaded at least one Chromium build. Cheaper than launching the
    # browser to test.
    if cache_dir.exists() and any(cache_dir.glob("chromium*")):
        return

    print(
        "Chromium not installed. Downloading (~140 MB, one-time)…",
        file=sys.stderr,
        flush=True,
    )
    res = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=False,
        check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(
            "Failed to install Chromium. Run manually:\n"
            "  python -m playwright install chromium"
        )


def _grab_brand_logo(url: str, page_html: str) -> str | None:
    """Return a ``data:image/...;base64,...`` URL for the site's brand logo.

    Multi-source fallback. Tries each candidate until one fetches successfully:

    1. ``<link rel="apple-touch-icon">`` (180x180 PNG, highest-quality brand mark)
    2. ``<link rel="apple-touch-icon-precomposed">``
    3. ``<link rel="icon">`` (largest sized variant wins)
    4. ``<meta property="og:image">`` (hero image — site brand)
    5. Google's favicon service (``s2/favicons?domain=X&sz=128``) — always returns

    Returns None only if every candidate including Google's service fails.
    Embeds as a ``data:`` URL so the resulting Marp deck is fully self-contained
    (no runtime fetch needed when rendering deck.html).
    """
    parsed = urlparse(url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = []

    for tag_match in re.finditer(
        r'<link[^>]+rel=["\'](?:apple-touch-icon|apple-touch-icon-precomposed)["\'][^>]+href=["\']([^"\']+)["\']',
        page_html or "",
        re.IGNORECASE,
    ):
        candidates.append(tag_match.group(1))

    icon_tags = list(
        re.finditer(
            r'<link[^>]+rel=["\'](?:icon|shortcut icon)["\'][^>]*>',
            page_html or "",
            re.IGNORECASE,
        )
    )
    sized: list[tuple[int, str]] = []
    for tag_match in icon_tags:
        tag = tag_match.group(0)
        href_m = re.search(r'href=["\']([^"\']+)["\']', tag)
        if not href_m:
            continue
        size_m = re.search(r'sizes=["\'](\d+)', tag)
        size = int(size_m.group(1)) if size_m else 16
        sized.append((size, href_m.group(1)))
    for _, href in sorted(sized, reverse=True):
        candidates.append(href)

    og_m = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        page_html or "",
        re.IGNORECASE,
    )
    if og_m:
        candidates.append(og_m.group(1))

    candidates.append(f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=128")

    with httpx.Client(timeout=5.0, follow_redirects=True) as client:
        for raw in candidates:
            try:
                absolute = (
                    raw if raw.startswith(("http://", "https://", "data:")) else urljoin(domain_root, raw)
                )
                if absolute.startswith("data:"):
                    return absolute
                r = client.get(absolute, headers={"User-Agent": "consent-engine/0.3 (+brand-logo)"})
                if r.status_code != 200 or not r.content:
                    continue
                mime = (r.headers.get("content-type", "image/png").split(";")[0] or "image/png").strip()
                if not mime.startswith("image/"):
                    continue
                b64 = base64.b64encode(r.content).decode("ascii")
                return f"data:{mime};base64,{b64}"
            except Exception:  # noqa: BLE001
                continue
    return None


def _derive_action_items(
    audit_result: AuditResult, scan: ScanResult
) -> tuple[list[str], list[str]]:
    """Translate findings + scan signals into actionable remediation + open gaps.

    Returns (remediation, open_gaps). Both are HTML-safe strings (rendered with
    `| safe`) so we can use <code> spans + <strong> for vocabulary that buyers
    recognize from their GTM container UI.
    """
    remediation: list[str] = []
    open_gaps: list[str] = []

    # Per-finding remediation — vendor-specific where useful, generic otherwise.
    for finding in audit_result.findings:
        if finding.status != "confirmed_violation":
            continue
        vendor_name = finding.vendor.name
        cookies = ", ".join(f"<code>{c}</code>" for c in finding.cookies_observed)
        gcs_raw = audit_result.gcs_value.raw if audit_result.gcs_value else "none"

        if vendor_name == "Meta":
            remediation.append(
                f"<strong>Meta Pixel ({cookies})</strong> fired despite GCS={gcs_raw}. "
                "In GTM, open the Meta/Facebook Pixel tag and set its consent settings to require "
                "<code>ad_storage</code>, <code>analytics_storage</code>, <code>ad_user_data</code>, "
                "and <code>ad_personalization</code>. Verify the reject-all path in the CMP banner "
                "maps to those four denied signals."
            )
        elif vendor_name == "Google Analytics":
            remediation.append(
                f"<strong>Google Analytics ({cookies})</strong> — ACM partial: cookieless "
                f"pings ARE firing correctly (GCS={gcs_raw} present in network), but "
                f"<code>_ga</code> / <code>_ga_&lt;id&gt;</code> cookies were ALSO set on this "
                "fresh-context session. Per Google's docs, denied <code>analytics_storage</code> "
                "should suppress both cookies and identifiers. The cookieless-ping layer is "
                "working; the cookie-suppression layer is not. Fix: in GA4 admin, confirm "
                "Consent Mode is set to <em>Advanced</em>. In GTM, open the GA4 Configuration "
                "tag and verify Additional Consent Settings require all four storage signals "
                "(<code>ad_storage</code>, <code>analytics_storage</code>, "
                "<code>ad_user_data</code>, <code>ad_personalization</code>)."
            )
        elif vendor_name in ("Google", "Google / DoubleClick"):
            remediation.append(
                f"<strong>Google Ads ({cookies})</strong> conversion linker fired despite opted-out. "
                "In GTM, open the Google Ads / Conversion Linker tag and enable "
                "<code>ads_data_redaction</code>. Confirm Additional Consent Settings require "
                "<code>ad_storage</code> + <code>ad_user_data</code> + <code>ad_personalization</code>."
            )
        elif vendor_name == "Dynatrace":
            remediation.append(
                f"<strong>Dynatrace RUM ({cookies})</strong> is firing without consent. Either "
                "(a) gate the Dynatrace tag in GTM behind <code>functional_storage = granted</code>, "
                "or (b) call <code>dtrum.disable()</code> on page load when consent is denied."
            )
        elif vendor_name == "Dynamic Yield":
            remediation.append(
                f"<strong>Dynamic Yield ({cookies})</strong> personalization is firing without "
                "consent. In GTM, gate the Dynamic Yield script tag behind "
                "<code>functional_storage = granted</code> or load it via "
                "<code>DY.recommendationContext</code> only after the CMP accepts."
            )
        else:
            remediation.append(
                f"<strong>{vendor_name} ({cookies})</strong> fired tracking despite GCS={gcs_raw}. "
                "Verify the tag has consent settings configured in your tag manager and that the "
                "CMP reject-all path maps to denied consent for the appropriate storage categories."
            )

    # Open gaps — items that need a human eye, not an auto-fix.
    cmp_cookies = {"OptanonConsent", "OptanonAlertBoxClosed", "OneTrust"}
    has_cmp_cookies = any(c.name in cmp_cookies for c in scan.cookies)
    if has_cmp_cookies and not audit_result.detected_cmp:
        open_gaps.append(
            "OneTrust cookies (<code>OptanonConsent</code>) were observed but the OneTrust JS API "
            "was not detected during the scan window. The CMP is likely loading asynchronously "
            "past the networkidle threshold. Manually verify by inspecting "
            "<code>window.OneTrust</code> in browser DevTools, then consider re-scanning with a "
            "longer wait."
        )

    requires_investigation = [
        f for f in audit_result.findings if f.status == "requires_investigation"
    ]
    if requires_investigation:
        vendors = ", ".join(f.vendor.name for f in requires_investigation)
        open_gaps.append(
            f"GCS=G111 observed on the opted-out scan for: {vendors}. The active CMP may be "
            "overriding our cookie-injection opt-out. Re-run with banner-click methodology to "
            "distinguish broken consent wiring from a stubborn CMP."
        )

    if audit_result.ssgtm_detected:
        open_gaps.append(
            f"<strong>Server-side GTM</strong> detected at <code>{audit_result.ssgtm_domain}</code>. "
            "Client-side consent enforcement scripts cannot block server-to-server calls, and the "
            "GPC (<code>Sec-GPC: 1</code>) header is not forwarded to server-side containers. "
            "Audit the sGTM container directly and verify every server tag has explicit consent "
            "gating."
        )

    if (
        audit_result.gpc_tested
        and audit_result.gpc_signal_respected is False
        and audit_result.gpc_vendors_after_signal > 0
    ):
        open_gaps.append(
            f"<strong>GPC signal not respected.</strong> "
            f"{audit_result.gpc_vendors_after_signal} tracking pixel"
            f"{'s' if audit_result.gpc_vendors_after_signal != 1 else ''} fired after "
            "<code>Sec-GPC: 1</code> was asserted. Under CCPA/CPRA this is enforceable "
            "non-compliance — California's CPPA has stated GPC violations are enforceable without "
            "prior notice."
        )

    return remediation, open_gaps


async def run_audit(
    url: str,
    *,
    jurisdiction: str | None = None,
    with_gpc: bool = True,
    firm_name: str | None = None,
    report_variant: str = "compliance",
    monthly_ad_spend_usd: int | None = None,
) -> AuditBundle:
    """Run a full forensic consent-compliance audit and return an `AuditBundle`.

    Args:
        url: The URL to audit.
        jurisdiction: Optional override (e.g., "EU", "US", "CA"). Auto-detected
            from the page HTML when omitted.
        with_gpc: When True, runs a second scan with the `Sec-GPC: 1` header
            asserted and compares pixel-firing counts. Populates gpc_* fields
            on the AuditResult so the report can show a clear pass/fail on
            whether the site respected the Global Privacy Control opt-out.

    Returns:
        AuditBundle — structured AuditResult, raw ScanResult (network log +
        cookies), the rendered HTML report, the LLM-written executive summary,
        and the Marp slide deck.
    """
    # SSRF guard — reject URLs resolving to private / loopback / metadata IPs.
    _validate_audit_url(url)

    audit_id = str(uuid.uuid4())

    # 0. First-run setup: download Chromium binaries if they aren't cached.
    ensure_chromium_installed()

    # 1. Primary S3 scan — consent pre-set to "reject all".
    scan, _ = await scan_page_fast(url=url, opted_out=True)

    # 1a. Post-scan CMP refinement. The in-scan CMP detector runs at
    #     networkidle, but some CMPs (Truyo, certain TrustArc deploys)
    #     finish loading later. Re-check the full network_requests list to
    #     catch late-loaded CMP CDNs that the in-scan detector missed.
    if not scan.detected_cmp or scan.cmp_detection_confidence == "low":
        net_cmp = detect_cmp_from_network_only(scan.network_requests)
        if net_cmp is not None and net_cmp.name != "unknown":
            scan.detected_cmp = net_cmp.name
            scan.cmp_detection_confidence = net_cmp.confidence

    # 1b. Optional GPC scan — same flow but with Sec-GPC: 1 header on every
    #     request + navigator.globalPrivacyControl injected. Compared against
    #     the primary scan to verify whether the site honors the legally
    #     binding opt-out signal under CCPA/CPRA.
    gpc_scan: ScanResult | None = None
    if with_gpc:
        gpc_scan, _ = await scan_page_fast(url=url, opted_out=True, gpc=True)

    # 1c. Final CMP refinement using BOTH scans + cookie names. Sites that
    #     load their CMP via GTM or other deferred mechanisms can miss the
    #     primary scan's networkidle window — Hydro-Québec is the canonical
    #     case: OneTrust loads ~3s after networkidle, so neither the in-scan
    #     JS-global check nor the primary network-URL pass sees it, but the
    #     GPC scan (which runs after) does. Pool both scans' URLs + cookies
    #     for the backstop check so a flaky primary doesn't leak through.
    if not scan.detected_cmp or scan.cmp_detection_confidence == "low":
        combined_urls = list(scan.network_requests)
        if gpc_scan is not None:
            combined_urls.extend(gpc_scan.network_requests)
        net_cmp = detect_cmp_from_network_only(combined_urls)
        if net_cmp is not None and net_cmp.name != "unknown":
            scan.detected_cmp = net_cmp.name
            scan.cmp_detection_confidence = net_cmp.confidence

    # 1d. Cookie-name backstop. Some CMPs (notably OneTrust on slow-loading
    #     pages) set their state cookie before their JS API mounts, so cookie
    #     evidence outlasts the network/JS evidence. Map well-known cookie
    #     names to their CMP so the report doesn't say "unknown CMP" when we
    #     can clearly see OptanonConsent in the jar.
    if not scan.detected_cmp:
        _COOKIE_TO_CMP = {
            "OptanonConsent": "OneTrust",
            "OptanonAlertBoxClosed": "OneTrust",
            "CookieConsent": "Cookiebot",
            "cookieyes-consent": "CookieYes",
            "didomi_token": "Didomi",
            "euconsent-v2": "IAB TCF",
            "OTAdditionalConsentString": "OneTrust",
        }
        all_cookies = list(scan.cookies) + (list(gpc_scan.cookies) if gpc_scan else [])
        for cookie in all_cookies:
            if cookie.name in _COOKIE_TO_CMP:
                scan.detected_cmp = _COOKIE_TO_CMP[cookie.name]
                scan.cmp_detection_confidence = "medium"
                break

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

    # 4b. GPC delta — count pixel firings under the GPC scan and compare.
    # Typed explicitly (no **dict unpack into AuditResult) so mypy strict
    # passes — see docs/release-v0.5.0/type-coverage.md for the rationale.
    gpc_tested = gpc_scan is not None
    gpc_header_sent = False
    gpc_navigator_api_set = False
    gpc_signal_respected: bool | None = None
    gpc_vendors_after_signal = 0
    gpc_pixel_count_baseline = 0
    gpc_pixel_count_with_gpc = 0
    if gpc_scan is not None:
        gpc_pixels = detect_pixel_firings(gpc_scan.network_requests)
        baseline_count = len(pixel_firings)
        gpc_count = len(gpc_pixels)
        # Respected when the GPC scan dropped to zero (or near-zero) tracking
        # pixels. "Near-zero" tolerance is 1 to account for cookieless ACM
        # modeling pings.
        respected = gpc_count <= 1 and baseline_count > 1
        gpc_header_sent = gpc_scan.gpc_header_sent
        gpc_navigator_api_set = True
        gpc_signal_respected = respected if baseline_count > 0 else None
        gpc_vendors_after_signal = gpc_count
        gpc_pixel_count_baseline = baseline_count
        gpc_pixel_count_with_gpc = gpc_count

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
        gpc_tested=gpc_tested,
        gpc_header_sent=gpc_header_sent,
        gpc_navigator_api_set=gpc_navigator_api_set,
        gpc_signal_respected=gpc_signal_respected,
        gpc_vendors_after_signal=gpc_vendors_after_signal,
        gpc_pixel_count_baseline=gpc_pixel_count_baseline,
        gpc_pixel_count_with_gpc=gpc_pixel_count_with_gpc,
    )

    # 5b. Derive concrete remediation steps + open gaps from the assembled
    #     AuditResult. These populate the "Remediation Steps" + "Open Gaps"
    #     sections in the HTML report.
    audit_result.remediation, audit_result.open_gaps = _derive_action_items(
        audit_result, scan
    )

    # 6. Wiki context retrieval (markdown KB, no vector DB).
    wiki_pages = await retrieve_context(audit_result)

    # 7. LLM executive summary (the only non-deterministic step).
    exec_summary = await generate_executive_summary(audit_result, wiki_pages)

    # 8. Brand logo extraction — best-effort fetch of the site's apple-touch-icon
    #    / favicon / og:image / Google s2 fallback. Embedded as data: URL so the
    #    deck stays self-contained.
    brand_logo_data_url = _grab_brand_logo(url, scan.page_html or "")

    # 9. HTML report + Marp slide deck.
    report_html = await generate_report(
        audit_result,
        wiki_pages,
        exec_summary,
        report_variant=report_variant,  # type: ignore[arg-type]
        estimated_monthly_ad_spend_usd=monthly_ad_spend_usd,
        firm_name=firm_name,
    )
    deck_md = generate_marp_slides(
        audit_result,
        exec_summary,
        brand="kjb",
        site_image_url=brand_logo_data_url,
        firm_name=firm_name,
        report_variant=report_variant,
        estimated_monthly_ad_spend_usd=monthly_ad_spend_usd,
    )

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
