"""Tool 7 — Regulatory Context Retriever (Wiki-based).

Uses the Karpathy LLM wiki pattern: reads index.md, selects relevant pages,
returns full page content as regulatory context. No vector DB or embeddings.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel

from consent_engine.models.audit_result import AuditResult, MethodologyFlag, ViolationStatus

_log = logging.getLogger(__name__)

_WIKI_ROOT = Path(__file__).parent.parent / "data" / "wiki"

# ---------------------------------------------------------------------------
# Audit finding → wiki page mapping
# ---------------------------------------------------------------------------

# Each entry is a list of wiki page paths relative to _WIKI_ROOT.
# Primary pages are listed first; secondary pages follow.
_FINDING_PAGE_MAP: dict[str, list[str]] = {
    "us_violation": [
        "regulations/ccpa.md",
        "regulations/us-state-laws.md",
        "concepts/gpc-signal.md",
        "enforcement/us-enforcement.md",
        "enforcement/us-class-actions.md",
        # live-fines-db.md is GDPR-only — EU clients only
    ],
    "gpc_violation": [
        "concepts/gpc-signal.md",
        "regulations/ccpa.md",
        "enforcement/us-enforcement.md",
        "enforcement/us-class-actions.md",
    ],
    "gcs_acm": [
        "concepts/consent-mode-v2.md",
        "technical/consent-mode-impact.md",
    ],
    "ssgtm": [
        "concepts/ssgtm-risk.md",
        "technical/google-tag-gateway.md",
        "enforcement/emerging-trends.md",
    ],
    "eu_jurisdiction": [
        "regulations/gdpr.md",
        "regulations/tcf.md",
        "enforcement/gdpr-fines.md",
        "enforcement/live-fines-db.md",
    ],
    "quebec": [
        "regulations/quebec-law25.md",
        "regulations/pipeda.md",
        "concepts/consent-mode-v2.md",
    ],
    "canada_federal": [
        "regulations/pipeda.md",
        "regulations/quebec-law25.md",
        "concepts/consent-mode-v2.md",
    ],
    "meta_tiktok_pixel": [
        "concepts/cipa-vppa.md",
        "enforcement/us-enforcement.md",
        "enforcement/us-class-actions.md",
        "enforcement/emerging-trends.md",
    ],
    "health_site": [
        "concepts/cipa-vppa.md",
        "enforcement/emerging-trends.md",
        "regulations/ccpa.md",
    ],
    "video_site": [
        "concepts/cipa-vppa.md",
        "enforcement/us-enforcement.md",
    ],
    "dark_patterns": [
        "concepts/dark-patterns.md",
        "regulations/gdpr.md",
        "enforcement/gdpr-fines.md",
    ],
    "cmp_failure": [
        "concepts/cmp-failures.md",
        "concepts/consent-mode-v2.md",
    ],
    "clean_scan": [
        "technical/consent-mode-impact.md",
        "concepts/consent-mode-v2.md",
    ],
}

# Vendors that trigger CIPA/VPPA pixel analysis
_PIXEL_VENDORS = {"meta", "facebook", "tiktok", "linkedin"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class WikiPage(BaseModel):
    path: str  # relative path within wiki
    title: str  # first H1 heading
    content: str  # full markdown content


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_METADATA_PREFIXES = (
    "tags:",
    "related:",
    "source:",
    "last_updated:",
    "total_records:",
    "total_cases:",
    "consent_related:",
)


def _strip_metadata_lines(content: str) -> str:
    """Remove wiki frontmatter lines (tags, related, source, etc.) from content.

    These lines are useful for tooling but clutter the HTML report display.
    The H1 heading and all ## sections are preserved intact.
    """
    lines = content.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip().lower()
        if any(stripped.startswith(prefix) for prefix in _METADATA_PREFIXES):
            continue
        cleaned.append(line)
    # Collapse runs of 3+ blank lines down to 2
    result: list[str] = []
    blank_count = 0
    for line in cleaned:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result)


def _read_page(relative_path: str) -> WikiPage | None:
    """Read a single wiki page. Returns None if file does not exist."""
    full_path = _WIKI_ROOT / relative_path
    if not full_path.exists():
        _log.warning("Wiki page not found: %s", full_path)
        return None
    content = full_path.read_text(encoding="utf-8")
    content = _strip_metadata_lines(content)
    # Extract first H1 as title
    title = relative_path
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break
    return WikiPage(path=relative_path, title=title, content=content)


def _select_page_keys(audit_result: AuditResult) -> list[str]:
    """Determine which finding keys apply based on audit result."""
    keys: list[str] = []

    jurisdiction = (audit_result.detected_jurisdiction or "US").upper()
    violations = [f for f in audit_result.findings if f.status == ViolationStatus.CONFIRMED]
    has_violations = bool(violations)

    # CCPA / CIPA / US-class-action wiki pages are US-specific. Load them only
    # for a US jurisdiction — an EU/UK or CA site gets its own regulatory context
    # below (eu_jurisdiction / quebec), so e.g. a Meta-pixel violation on a UK
    # site cites UK-GDPR, not California CIPA. (Previously these loaded for every
    # scan, flooding non-US reports with CCPA/CIPA/"Do Not Sell" prose.)
    is_us = jurisdiction == "US"
    if has_violations and is_us:
        keys.append("us_violation")

    # EU/Canada-specific regulatory context — only when jurisdiction warrants it.
    if jurisdiction == "EU":
        keys.append("eu_jurisdiction")
    elif "QC" in jurisdiction or "QUEBEC" in jurisdiction:
        keys.append("quebec")
    elif jurisdiction in ("CA", "CANADA"):
        # Quebec Law 25 is the binding ceiling for nearly all CA-facing sites
        # (extraterritorial + de facto Canadian baseline). PIPEDA is the federal
        # floor. Pull both. The report writer surfaces Law 25 first.
        keys.append("quebec")

    # If the CMP itself reports a GDPR template (common pattern: Canadian
    # orgs serving the stricter Law 25 + GDPR hybrid template, EU orgs on
    # .com domains, anyone applying GDPR as the global default), also pull
    # the EU regulatory pages so the report cites both frameworks. This is
    # additive — runs alongside the jurisdiction keys above.
    rc = audit_result.cmp_runtime_config
    if rc is not None:
        cmp_signals = " ".join(
            s for s in (rc.template_name, rc.geolocation_rule) if s
        ).lower()
        if "gdpr" in cmp_signals and "eu_jurisdiction" not in keys:
            keys.append("eu_jurisdiction")

    # GPC signal — GPC is a legally binding opt-out only under US state law, so
    # the GPC-enforcement pages (CCPA + US class actions) load only for US.
    if audit_result.gpc_tested and has_violations and is_us:
        keys.append("gpc_violation")

    # GCS / ACM — two distinct cases:
    # 1. G100/G110/G101 (denial confirmed) → ACM pings active, pull ACM pages
    # 2. G111 in S3 opt-out test (granted state post-opt-out) → CMP integration failure
    #    The CMP is not propagating denial to Consent Mode — pull cmp_failure pages instead.
    if audit_result.gcs_value:
        gcs = audit_result.gcs_value.raw
        if len(gcs) >= 4 and "0" in gcs[2:]:
            keys.append("gcs_acm")
        elif (
            audit_result.methodology == MethodologyFlag.S3 and len(gcs) >= 4 and "0" not in gcs[2:]
        ):
            # Granted state during opt-out test = CMP not updating Consent Mode
            keys.append("cmp_failure")

    # SSGTM
    if audit_result.ssgtm_detected:
        keys.append("ssgtm")

    # Pixel vendors — CIPA/VPPA are US wiretap statutes, so these pages are
    # US-only. On an EU/UK/CA site the same pixel is covered by the local regime.
    if violations and is_us:
        vendor_names = {f.vendor.name.lower() for f in violations}
        if vendor_names & _PIXEL_VENDORS:
            keys.append("meta_tiktok_pixel")

    # Clean scan
    if not has_violations:
        keys.append("clean_scan")

    # Always include CMP failure check if CMP was detected
    if audit_result.detected_cmp:
        keys.append("cmp_failure")

    return keys


def _deduplicated_pages(page_paths: list[str]) -> list[str]:
    """Return page paths deduplicated while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for p in page_paths:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def retrieve_context(
    audit_result: AuditResult,
    max_pages: int = 7,
) -> list[WikiPage]:
    """Retrieve relevant regulatory wiki pages for the audit result.

    Reads the wiki index to determine relevant pages, then reads those pages
    in full. Returns up to max_pages pages ordered by relevance priority.

    This replaces the Pinecone vector search with direct file reads.
    No embeddings, no external API calls, no chunking.

    Args:
        audit_result: The completed audit result to retrieve context for.
        max_pages: Maximum number of wiki pages to return.

    Returns:
        List of WikiPage objects with full markdown content.
        Returns empty list if wiki directory is not found.
    """
    if not _WIKI_ROOT.exists():
        _log.error("Wiki root not found: %s", _WIKI_ROOT)
        return []

    # Determine which finding keys apply
    keys = _select_page_keys(audit_result)
    if not keys:
        keys = ["clean_scan"]

    # Collect page paths in priority order
    all_paths: list[str] = []
    for key in keys:
        all_paths.extend(_FINDING_PAGE_MAP.get(key, []))

    # Deduplicate preserving priority order, cap at max_pages
    selected_paths = _deduplicated_pages(all_paths)[:max_pages]

    # Read pages
    pages: list[WikiPage] = []
    for path in selected_paths:
        page = _read_page(path)
        if page:
            pages.append(page)

    _log.info(
        "Retrieved %d wiki pages for audit of %s (keys: %s)",
        len(pages),
        audit_result.url,
        ", ".join(keys),
    )
    return pages
