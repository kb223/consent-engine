"""Tool 8 — Audit Report Generator. Output: HTML via Jinja2.

Two variants:
- ``signal``    — Signal Recovery framing for growth/CMO buyer; shows $/mo recoverable
- ``compliance`` — Legal/risk framing for privacy/legal buyer (default; preserves prior output)
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from consent_engine.config import get_settings
from consent_engine.llm.client import LLMClient
from consent_engine.models.audit_result import (
    AuditResult,
    MethodologyFlag,
    VendorFinding,
    ViolationStatus,
)
from consent_engine.tools.tool_07_rag_retriever import WikiPage

ReportVariant = Literal["signal", "compliance"]

# Share of US population in CCPA-like opt-out-protected states (CA, CO, CT, VA,
# UT, TX, OR, MT, IA, DE, NJ, NH, TN, NE, MN, MD, RI plus pending — ~35% of US
# population is in a state with a binding opt-out right as of 2026).
_US_OPTOUT_MARKET_RATE: float = 0.35
# Share of consent-denied traffic that can be recovered via proper sGTM + CAPI + ACM.
_RECOVERY_UPLIFT: float = 0.50

# Brand-tier auto-estimation: scan signals → (label, default monthly ad spend,
# typical ROAS multiplier). Used when the buyer hasn't self-reported
# --monthly-ad-spend, so the dollar math defaults to numbers that match the
# actual scale of the company being audited (not a generic mid-market anchor).
_BRAND_TIERS: list[tuple[str, int, float]] = [
    # (tier_label, monthly_ad_spend_usd, roas_multiplier)
    ("Global Enterprise",       10_000_000, 7.0),  # multi-domain, sGTM, 15+ vendors
    ("National Enterprise",      2_000_000, 6.0),  # single-domain, sophisticated CMP, 8+ vendors
    ("Mid-Large / Multi-Channel",  500_000, 5.5),  # OneTrust/Truyo/Cookiebot, 5-7 vendors
    ("Mid-Market",                 100_000, 5.0),  # established CMP, 3-5 vendors
    ("SMB",                         20_000, 4.0),  # basic stack, <3 vendors
]


def _estimate_brand_tier(audit_result: AuditResult) -> tuple[str, int, float]:
    """Return ``(tier_label, monthly_ad_spend_usd, roas_multiplier)`` from the scan.

    Used when the buyer doesn't self-report ``--monthly-ad-spend``. Scores brand
    sophistication from observable signals (vendor count, sGTM presence,
    enterprise CMP) and maps to the matching tier in ``_BRAND_TIERS``. Bigger
    brands get bigger defaults so the recoverable-revenue math doesn't default
    to peanut numbers when the audit is run against a national enterprise site.
    """
    vendor_count = len(audit_result.findings)
    pixel_count = len(audit_result.pixel_firings)
    has_ssgtm = audit_result.ssgtm_detected
    # Enterprise-grade CMPs — running these signals significant procurement +
    # legal involvement, which correlates with enterprise ad budgets.
    enterprise_cmp = {
        "OneTrust", "Truyo", "TrustArc", "Usercentrics", "Sourcepoint",
        "Didomi", "Cookiebot", "Ketch",
    }
    has_enterprise_cmp = audit_result.detected_cmp in enterprise_cmp

    score = 0
    score += min(vendor_count, 10)         # up to 10 from vendor breadth
    score += min(pixel_count, 6)           # up to 6 from pixel endpoint diversity
    score += 6 if has_ssgtm else 0         # sGTM = enterprise infrastructure
    score += 3 if has_enterprise_cmp else 0

    if score >= 18:
        return _BRAND_TIERS[0]  # Global Enterprise
    if score >= 13:
        return _BRAND_TIERS[1]  # National Enterprise
    if score >= 8:
        return _BRAND_TIERS[2]  # Mid-Large
    if score >= 4:
        return _BRAND_TIERS[3]  # Mid-Market
    return _BRAND_TIERS[4]      # SMB

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# KJB logo — read from bundled PNG so it renders in Playwright file:// PDF context
_RSC_LOGO_PATH = Path(__file__).parent.parent / "rsc-logo.png"
_RSC_ICON_B64: str = (
    base64.b64encode(_RSC_LOGO_PATH.read_bytes()).decode() if _RSC_LOGO_PATH.exists() else ""
)

_METHODOLOGY_LABELS: dict[str, str] = {
    MethodologyFlag.S1: "Baseline (Public Privacy Gap Check)",
    MethodologyFlag.S3: "Definitive (Privacy Logic Enforcement)",
    MethodologyFlag.S3_CONSENT_WIRING_BROKEN: (
        "Definitive (Consent Wiring Broken: tags fire regardless of CMP state)"
    ),
    MethodologyFlag.INCONCLUSIVE_UNKNOWN_CMP: (
        "Inconclusive (CMP not recognised, injection unverified)"
    ),
}


def _render_markdown(text: str) -> Markup:
    """Convert markdown text to safe HTML for Jinja2 rendering."""
    return Markup(md_lib.markdown(text, extensions=["nl2br", "tables", "sane_lists"]))


def _reg_excerpt(text: str, max_sections: int = 3) -> str:
    """Extract the first N ## sections from a wiki page for the regulatory basis display.

    Full content is passed to the LLM for executive summary generation.
    The report UI shows a focused excerpt — enough for legal reference, not a wall of text.
    Strips the H1 title (already shown as reg-source label) and limits depth.
    """
    lines = text.splitlines()
    # Skip the H1 title line and any blank lines following it
    start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("# ") and not line.strip().startswith("## "):
            start = i + 1
            break

    sections: list[list[str]] = []
    current: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") and current:
            sections.append(current)
            current = [line]
            if len(sections) >= max_sections:
                break
        else:
            current.append(line)
    if current and len(sections) < max_sections:
        sections.append(current)

    excerpt = "\n".join("\n".join(s) for s in sections[:max_sections])
    return excerpt.strip()


def _get_jinja_env() -> Environment:
    # autoescape=True unconditionally. select_autoescape(["html"]) keys off the
    # final filename extension, and the template is "audit_report.html.j2" — the
    # ".j2" suffix means select_autoescape returned False, leaving autoescape OFF
    # and every {{ }} emitting raw HTML (stored XSS via the attacker-controlled
    # audited URL / cookie names). Force True. Intentional-HTML sinks are
    # markupsafe.Markup (the `markdown` filter) or explicitly `| safe` in the
    # template, both of which survive autoescape; site-derived values flowing
    # into the `| safe` action-item strings are escaped at construction in
    # audit.py::_derive_action_items.
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )
    env.filters["markdown"] = _render_markdown
    env.filters["reg_excerpt"] = _reg_excerpt
    return env


# Methodologies under which a CONFIRMED finding is legally defensible as a
# violation. Under INCONCLUSIVE_UNKNOWN_CMP we could not verify our opt-out
# injection took effect (unrecognized / un-injectable CMP), so findings are
# shown in the table as indicative only — they must NOT drive the "Consent
# Violation Detected" verdict, statutory-exposure dollars, or the executive
# summary. S1 is a baseline public-gap check, not a definitive enforcement scan.
_DEFINITIVE_METHODOLOGIES: frozenset[MethodologyFlag] = frozenset(
    {MethodologyFlag.S3, MethodologyFlag.S3_CONSENT_WIRING_BROKEN}
)


def _confirmed_violations(audit_result: AuditResult) -> list[VendorFinding]:
    """CONFIRMED findings that count as defensible violations for the verdict.

    Gated on methodology: returns an empty list unless the scan methodology is
    definitive. This is the single source of truth for "violations that drive a
    claim" — the verdict band, exposure estimate, executive summary, and deck all
    route through it so an inconclusive scan can never render a confirmed-violation
    verdict or a dollar figure. The findings table still iterates
    ``audit_result.findings`` directly, so observations remain visible as
    indicative.
    """
    if audit_result.methodology not in _DEFINITIVE_METHODOLOGIES:
        return []
    return [f for f in audit_result.findings if f.status == ViolationStatus.CONFIRMED]


def estimate_recoverable_revenue(
    audit_result: AuditResult,
    monthly_ad_spend_usd: int | None = None,
) -> dict[str, int | float | str | bool]:
    """Estimate the monthly **conversion value** recoverable by fixing the stack.

    Formula:
        ad_revenue        = monthly_ad_spend × ROAS
        monthly_recovered = ad_revenue × US_opt_out_rate × signal_gap × recovery_uplift

    The output is *recovered conversion value*, not "ad spend not wasted" — that
    distinction matters at enterprise scale, where a 4% signal gap on $5M/mo of
    ad-attributable revenue ($30M+ with ROAS) is six figures, not four.

    Auto-tiers brand size from scan signals when the buyer hasn't self-reported
    ``--monthly-ad-spend``. Without auto-tiering, the formula defaulted to a
    mid-market anchor that understates enterprise impact by 50-100×.

    ``signal_gap`` scales 0.0 → 1.0 based on observable defects in the scan:
    each confirmed cookie violation, post-denial pixel firing, sGTM presence,
    and partial/broken Consent Mode state adds to the gap. Capped at 1.0.

    Kept defensible in a sales conversation: every input is either user-reported
    or derived from the same AuditResult the rest of the report is built on.
    """
    # Brand-tier auto-estimation provides defaults when the buyer hasn't
    # self-reported spend. ROAS is always derived from the tier — even with a
    # user-reported spend, we want the recovery framing in revenue terms.
    tier_label, tier_default_spend, roas = _estimate_brand_tier(audit_result)

    spend = (
        monthly_ad_spend_usd
        if monthly_ad_spend_usd and monthly_ad_spend_usd > 0
        else tier_default_spend
    )

    violations = _confirmed_violations(audit_result)
    pixel_violations = [p for p in audit_result.pixel_firings if not p.is_acm_ping]

    gcs_state = audit_result.gcs_value.raw if audit_result.gcs_value else ""
    gcs_full_denial = bool(
        gcs_state and len(gcs_state) >= 4 and gcs_state[2] == "0" and gcs_state[3] == "0"
    )
    gcs_partial = bool(
        gcs_state and len(gcs_state) >= 4 and "0" in gcs_state[2:] and not gcs_full_denial
    )
    gcs_cmp_broken = bool(
        gcs_state
        and audit_result.methodology
        in (MethodologyFlag.S3, MethodologyFlag.S3_CONSENT_WIRING_BROKEN)
        and len(gcs_state) >= 4
        and "0" not in gcs_state[2:]
    )

    # Per-defect contribution to the signal gap (capped at 1.0 total).
    gap = 0.0
    gap += min(len(violations) * 0.04, 0.25)  # up to 25% from cookie violations
    gap += min(len(pixel_violations) * 0.03, 0.30)  # up to 30% from pixel leakage
    if audit_result.ssgtm_detected:
        gap += 0.08  # sGTM bypass adds fixed premium
    if gcs_cmp_broken:
        gap += 0.15  # CMP integration failure
    elif gcs_partial:
        gap += 0.08  # partial opt-out = partial loss
    if not audit_result.detected_cmp:
        gap += 0.05  # no CMP detected = no consent plumbing
    gap = min(gap, 1.0)

    # Ad-attributable monthly revenue = spend × ROAS (e.g. $2M × 6x = $12M).
    ad_attributable_revenue = int(spend * roas)
    # Monthly recovered conversion value at full signal gap on opt-out traffic.
    monthly_recoverable = int(
        ad_attributable_revenue * _US_OPTOUT_MARKET_RATE * gap * _RECOVERY_UPLIFT
    )
    monthly_recoverable_low = int(monthly_recoverable * 0.6)
    monthly_recoverable_high = int(monthly_recoverable * 1.4)
    annual_recoverable = monthly_recoverable * 12

    return {
        "monthly_ad_spend_usd": spend,
        "ad_spend_user_provided": bool(monthly_ad_spend_usd and monthly_ad_spend_usd > 0),
        "brand_tier_label": tier_label,
        "roas_multiplier": roas,
        "ad_attributable_revenue_usd": ad_attributable_revenue,
        "signal_gap_pct": round(gap * 100, 1),
        "consent_loss_rate_pct": int(_US_OPTOUT_MARKET_RATE * 100),
        "recovery_uplift_pct": int(_RECOVERY_UPLIFT * 100),
        "monthly_recoverable_usd": monthly_recoverable,
        "monthly_recoverable_low_usd": monthly_recoverable_low,
        "monthly_recoverable_high_usd": monthly_recoverable_high,
        "annual_recoverable_usd": annual_recoverable,
        "has_recovery_opportunity": monthly_recoverable > 0,
        "gcs_full_denial": gcs_full_denial,
    }


_PIXEL_VENDORS_LOWER: frozenset[str] = frozenset({"meta", "facebook", "tiktok", "linkedin"})

_WIKI_ENFORCEMENT_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "wiki"
    / "enforcement"
    / "us-class-actions.md"
)


def _parse_amount(amount_str: str) -> int | None:
    """Parse amount strings from wiki tables ('$1.2M', '$275M', '$5K/violation') → int USD.

    Returns None for non-numeric values ('Varies', 'Class exposure', 'Pending', 'Settlement').
    """
    import re

    s = amount_str.strip().lstrip("$").replace(",", "").replace(" ", "")
    m = re.match(r"^([\d.]+)([KMB])?", s)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    suffix = (m.group(2) or "").upper()
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
    return int(value * mult)


def _load_enforcement_anchors() -> dict[str, dict[str, object]]:
    """Parse the 'Key Enforcement Principles' table from the live wiki.

    Returns a dict keyed by statute keyword (ccpa, cipa, vppa, coppa, ftc_act, cmia, bipa)
    with {case, amount_usd, raw_amount, principle, statute}. Each call re-reads the wiki —
    `scripts/ingest_us_enforcement.py` refreshes propagate automatically on next report.

    Falls back to an empty dict if the wiki page is missing or unparseable; callers use
    conservative hardcoded defaults in that case.
    """
    import re

    if not _WIKI_ENFORCEMENT_PATH.exists():
        return {}
    text = _WIKI_ENFORCEMENT_PATH.read_text(encoding="utf-8")

    header_match = re.search(
        r"##\s+Key Enforcement Principles[^\n]*\n(.*?)(?:\n---|\n##\s)",
        text,
        re.DOTALL,
    )
    if not header_match:
        return {}
    section = header_match.group(1)

    anchors: dict[str, dict[str, object]] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() == "principle":
            continue
        principle, case, amount_raw, statute = cells[0], cells[1], cells[2], cells[3]
        amount_usd = _parse_amount(amount_raw)

        statute_lower = statute.lower()
        keys: list[str] = []
        # CMIA-combined settlements sit in the 'cmia' bucket only — keeping them out of
        # the pure-CCPA bucket preserves Sephora-class baseline as the CCPA anchor.
        is_cmia_combo = "cmia" in statute_lower
        if ("ccpa" in statute_lower or "cpra" in statute_lower) and not is_cmia_combo:
            keys.append("ccpa")
        if is_cmia_combo:
            keys.append("cmia")
        if "coppa" in statute_lower:
            keys.append("coppa")
        if "ftc act" in statute_lower or "ftc §5" in statute_lower:
            keys.append("ftc_act")
        if "cipa" in statute_lower:
            keys.append("cipa")
        if "vppa" in statute_lower:
            keys.append("vppa")
        if "bipa" in statute_lower:
            keys.append("bipa")

        for key in keys:
            # Keep the largest anchor per statute (most conservative high band).
            existing = anchors.get(key)
            existing_amount = existing.get("amount_usd") if existing else None
            if (
                existing is None
                or (
                    amount_usd is not None
                    and isinstance(existing_amount, int)
                    and amount_usd > existing_amount
                )
                or (amount_usd is not None and existing_amount is None)
            ):
                anchors[key] = {
                    "case": case,
                    "amount_usd": amount_usd,
                    "raw_amount": amount_raw,
                    "principle": principle,
                    "statute": statute,
                }
    return anchors


def estimate_exposure_usd(
    audit_result: AuditResult,
) -> dict[str, object]:
    """Estimate statutory + class-action exposure from observable violations.

    Anchored to settled case outcomes pulled live from
    `data/wiki/enforcement/us-class-actions.md` (Key Enforcement Principles table)
    rather than hardcoded amounts. Refreshing the wiki updates exposure bands
    automatically — add a larger CCPA settlement to the table and next report reflects it.

    Tiers are additive: baseline CCPA for any confirmed violation, CIPA pixel wiretap
    when Meta/TikTok/LinkedIn pixel leakage is present, sGTM premium for first-party
    forwarding. Definitive evidence of broken consent wiring amplifies the high
    band 1.5x (intentionality finding → statutory max more likely).
    """
    # Methodology gate: no statutory / class-action exposure is defensible unless
    # the scan methodology is definitive. Under INCONCLUSIVE we could not verify
    # consent denial took effect, so neither the CCPA tier (driven by `violations`)
    # nor the CIPA pixel tier (driven by `pixel_firings`, independent of
    # `violations`) may emit a dollar figure. Return zero exposure.
    if audit_result.methodology not in _DEFINITIVE_METHODOLOGIES:
        return {
            "has_exposure": False,
            "total_exposure_low_usd": 0,
            "total_exposure_high_usd": 0,
            "components": [],
            "anchors_sourced_from_wiki": False,
        }

    violations = _confirmed_violations(audit_result)
    pixel_violations = [p for p in audit_result.pixel_firings if not p.is_acm_ping]

    has_pixel_leak = bool(pixel_violations) or any(
        v.vendor.name.lower() in _PIXEL_VENDORS_LOWER for v in violations
    )

    anchors = _load_enforcement_anchors()

    def _anchor_for(
        key: str,
        fallback_case: str,
        fallback_usd: int,
    ) -> tuple[str, int]:
        a = anchors.get(key)
        if a:
            amt = a.get("amount_usd")
            if isinstance(amt, int):
                label = f"{a['case']}: {a['raw_amount']} — {a.get('principle', '')}".rstrip(" —")
                return label, amt
        return fallback_case, fallback_usd

    components: list[dict[str, object]] = []
    low = 0
    high = 0

    if violations:
        ccpa_anchor, ccpa_high = _anchor_for("ccpa", "Sephora (CA AG, 2022): $1.2M", 1_200_000)
        ccpa_low = max(100_000, ccpa_high // 12)
        low += ccpa_low
        high += ccpa_high
        components.append(
            {
                "statute": "CCPA §1798.150 / CPRA",
                "low_usd": ccpa_low,
                "high_usd": ccpa_high,
                "anchor": ccpa_anchor,
            }
        )

    if has_pixel_leak:
        # CMIA+CCPA is the current high-water mark for pixel-on-sensitive-site
        # settlements (Aspen Dental). Fall back to CIPA if CMIA anchor missing.
        pixel_anchor, pixel_high = _anchor_for("cmia", "", 0)
        if not pixel_anchor or pixel_high == 0:
            pixel_anchor, pixel_high = _anchor_for(
                "cipa",
                "Aspen Dental: $18.5M (FTC/state AGs); Meta Pixel class settlements $1M-$50M",
                18_500_000,
            )
        pixel_low = max(1_000_000, pixel_high // 18)
        low += pixel_low
        high += pixel_high
        components.append(
            {
                "statute": "CIPA §631 (pixel-as-wiretap)",
                "low_usd": pixel_low,
                "high_usd": pixel_high,
                "anchor": pixel_anchor,
            }
        )

    if audit_result.ssgtm_detected and has_pixel_leak:
        # Scale sGTM premium off the pixel anchor — industry settlements grow, premium grows.
        _, pixel_ref = _anchor_for("cmia", "", 0)
        if pixel_ref == 0:
            _, pixel_ref = _anchor_for("cipa", "", 18_500_000)
        sgtm_high = max(10_000_000, pixel_ref // 2)
        sgtm_low = max(500_000, sgtm_high // 20)
        low += sgtm_low
        high += sgtm_high
        components.append(
            {
                "statute": "sGTM first-party forwarding",
                "low_usd": sgtm_low,
                "high_usd": sgtm_high,
                "anchor": "First-party server relay is not a CIPA defense (emerging trend)",
            }
        )

    if audit_result.methodology == MethodologyFlag.S3_CONSENT_WIRING_BROKEN and low > 0:
        high = int(high * 1.5)
        components.append(
            {
                "statute": "Aggravated (evidence of intentional violation)",
                "low_usd": 0,
                "high_usd": 0,
                "anchor": "Tags fire regardless of CMP state: supports intentionality finding",
            }
        )

    return {
        "has_exposure": low > 0,
        "total_exposure_low_usd": low,
        "total_exposure_high_usd": high,
        "components": components,
        "anchors_sourced_from_wiki": bool(anchors),
    }


def _safe_prompt_url(url: str) -> str:
    """Sanitize the audited URL before interpolating it into an LLM prompt.

    The URL is attacker-controlled, and its query/fragment is the natural carrier
    for a prompt-injection payload (e.g. ``?q=ignore+all+prior+instructions...``).
    Strip to ``scheme://host/path``, drop query + fragment, collapse newlines, and
    truncate so a hostile URL cannot steer the model-written executive summary. The
    deterministic findings are computed in Python and are unaffected regardless.
    """
    try:
        p = urlparse(url)
    except ValueError:
        return "(url unavailable)"
    base = f"{p.scheme}://{p.netloc}{p.path}" if p.scheme and p.netloc else url
    return base.replace("\n", " ").replace("\r", " ").strip()[:200]


def _build_executive_summary_prompt(
    audit_result: AuditResult,
    wiki_pages: list[WikiPage],
    variant: ReportVariant = "compliance",
    recovery: dict[str, int | float | str | bool] | None = None,
) -> str:
    violations = _confirmed_violations(audit_result)

    if violations:
        vendors = ", ".join(f.vendor.name for f in violations)
        violation_text = (
            f"Confirmed violations: {vendors} set tracking cookies despite opted-out consent."
        )
    else:
        violation_text = "No confirmed cookie violations detected."

    gcs_state = audit_result.gcs_value.raw if audit_result.gcs_value else "MISSING"
    _es_gcs_any_denial = bool(
        audit_result.gcs_value and len(gcs_state) >= 4 and "0" in gcs_state[2:]
    )
    _es_gcs_full_denial = bool(
        audit_result.gcs_value
        and len(gcs_state) >= 4
        and gcs_state[2] == "0"
        and gcs_state[3] == "0"
    )
    _es_gcs_partial = (
        _es_gcs_any_denial and not _es_gcs_full_denial
    )  # e.g. G101: ads denied, analytics granted
    _es_gcs_cmp_broken = bool(
        audit_result.gcs_value
        and audit_result.methodology
        in (MethodologyFlag.S3, MethodologyFlag.S3_CONSENT_WIRING_BROKEN)
        and len(gcs_state) >= 4
        and "0" not in gcs_state[2:]
    )
    if _es_gcs_full_denial:
        acm_note = (
            f"Advanced Consent Mode correctly implemented (GCS={gcs_state}): "
            f"Google tags are sending cookieless modeling pings only — no PII cookie IDs transmitted. "
            f"The confirmed violations above are from non-Google vendors that set tracking cookies "
            f"despite denial, which is the primary legal exposure."
        )
    elif _es_gcs_partial:
        _partial_ad_denied = len(gcs_state) >= 3 and gcs_state[2] == "0"
        _partial_analytics_denied = len(gcs_state) >= 4 and gcs_state[3] == "0"
        _partial_what = (
            "ad_storage denied, analytics_storage still granted"
            if _partial_ad_denied and not _partial_analytics_denied
            else "analytics_storage denied, ad_storage still granted"
            if _partial_analytics_denied and not _partial_ad_denied
            else "partial denial"
        )
        acm_note = (
            f"Partial Consent Mode opt-out detected (GCS={gcs_state}): {_partial_what}. "
            f"The CMP only partially propagates user consent denial — users who opt out of ads "
            f"remain tracked for analytics purposes. Under CCPA, a 'Do Not Sell' opt-out must "
            f"halt all data sharing for targeted advertising AND analytics profiling."
        )
    elif _es_gcs_cmp_broken:
        acm_note = (
            f"Consent Mode detected (GCS={gcs_state}) but CMP integration is broken: "
            f"after opt-out, Consent Mode remains in granted state instead of updating to denial (G100). "
            f"This means the CMP is not propagating user consent choices to Google tags."
        )
    else:
        acm_note = f"GCS signal: {gcs_state}."

    cmp_note = (
        f"CMP: {audit_result.detected_cmp} ({audit_result.cmp_detection_confidence} confidence), "
        f"interaction: {audit_result.cmp_interaction_method}."
        if audit_result.detected_cmp
        else "No known CMP detected."
    )

    ssgtm_note = (
        f"SSGTM detected at {audit_result.ssgtm_domain}. "
        f"Client-side JavaScript cannot block server-to-server calls — "
        f"consent enforcement may not extend to server-side data flows."
        if audit_result.ssgtm_detected
        else "SSGTM: not detected."
    )

    gpc_note = (
        "GPC signal (Sec-GPC: 1) was detected. "
        "Under CCPA/CPRA, GPC is a mandatory opt-out mechanism. "
        "California's CPPA has stated GPC non-compliance is enforceable without prior notice."
        if audit_result.gpc_tested and violations
        else ""
    )

    # Build regulatory context from full wiki page content (not truncated chunks)
    wiki_context = "\n\n---\n\n".join(f"## {page.title}\n\n{page.content}" for page in wiki_pages)

    if variant == "signal":
        recovery_line = ""
        if recovery and recovery.get("has_recovery_opportunity"):
            recovery_line = (
                f"- Estimated recoverable ad revenue at current spend: "
                f"${recovery['monthly_recoverable_low_usd']:,}-${recovery['monthly_recoverable_high_usd']:,}/mo "
                f"(signal gap {recovery['signal_gap_pct']}%)."
            )
        return f"""You are a measurement-ops consultant writing an Executive Summary for a growth/CMO audience.
Tone: direct, technical, data-driven. Growth framing — ad AI and scale, not legal risk. No filler phrases. No em dashes. No hedging.

AUDIT FACTS:
- URL: {_safe_prompt_url(audit_result.url)}
- {violation_text}
- {acm_note}
- {cmp_note}
- {ssgtm_note}
{f'- {gpc_note}' if gpc_note else ''}
{recovery_line}

REGULATORY KNOWLEDGE BASE (for context — do NOT lead with legal framing):
{wiki_context}

TASK: Write 3-4 sentences summarizing the audit from a growth/scale perspective.

Rules:
- Frame every finding as a signal-quality problem feeding ad AI (Meta Advantage+, Performance Max, TikTok Smart+).
- Lead with the biggest scale ceiling: broken consent wiring > sGTM gap > partial GCS > pixel leakage > clean.
- If violations exist: describe them as "signal the ad AI is not receiving" or "data the ad platform cannot optimize on" — not as legal violations.
- If recoverable-revenue estimate is provided, cite the $/mo range as the scale unlock.
- If SSGTM detected without server-side conversions: frame as "server events never reach ad AI."
- If GCS=G100 (both denied) with violations: note ACM is configured correctly; the gap is the non-Google vendors leaking signal out.
- If GCS=G101 (partial): frame as partial signal loss — analytics AI still optimizing on data that consent denied.
- If clean: state the stack is AI-ready and note what that unlocks.
- Use "ad AI", "scale ceiling", "signal", "first-party data" — avoid "violation", "liability", "fine", "lawsuit".
- Never start with "In this audit", "It is important to note", or similar filler.
- Never use em dashes."""

    return f"""You are a privacy compliance consultant writing a concise Executive Summary for a consent audit report.
Tone: direct, technical, data-driven. No filler phrases. No em dashes. No hedging.

AUDIT FACTS:
- URL: {_safe_prompt_url(audit_result.url)}
- Jurisdiction: {audit_result.detected_jurisdiction or 'US'}
- {violation_text}
- {acm_note}
- {cmp_note}
- {ssgtm_note}
{f'- {gpc_note}' if gpc_note else ''}

REGULATORY KNOWLEDGE BASE:
{wiki_context}

TASK: Write 3-4 sentences summarizing the audit findings.

Rules:
- Lead with the most material legal risk (confirmed violation > GPC violation > ACM gray area > clean).
- If violations exist: cite the specific statute (CCPA §1798.120, CPRA sharing extension, GDPR Article 6) and fine exposure.
- If GPC was detected with violations: state explicitly that GPC is a mandatory opt-out under CCPA and that non-compliance is immediately enforceable.
- If GCS=G100 (both denied) present with confirmed violations: note that Advanced Consent Mode is correctly implemented (cookieless pings only, no PII cookie IDs transmitted). The violations are the actual cookie sets by {vendors}, not the G100 pings. Do not frame G100 pings as a violation — they are compliant ACM behavior.
- If GCS=G101 (ad_storage denied, analytics_storage granted): this is a PARTIAL opt-out. The brand's CMP only denies ad tracking — analytics tracking continues post opt-out. Frame this as incomplete CCPA compliance: "Do Not Sell" must cover analytics profiling, not just ad delivery. This is still a compliance gap even though it shows partial effort.
- If SSGTM detected: note the server-side consent gap risk.
- If clean: state it plainly and note ACM modeling activity if present.
- Use specific enforcement case names or fine amounts from the regulatory context where relevant.
- NOTE: The scan was simulated using a California, USA geolocation and timezone. If the CMP was not visually detected but its underlying cookies were targeted for injection, this indicates IP-gating where the CMP is active globally but hidden from users outside specific regions. Mention this risk if applicable.
- Never start with "In this audit", "It is important to note", or similar filler.
- Never use em dashes."""


def _llm_key_available() -> bool:
    """Return True if any supported LLM provider has an API key configured.

    Checks the env vars LiteLLM actually reads:

    - ``GEMINI_API_KEY``    — for ``gemini/...`` models (default)
    - ``ANTHROPIC_API_KEY`` — for ``claude-...`` models
    - ``OPENAI_API_KEY``    — for ``gpt-...`` / ``o1-...`` models
    - ``GOOGLE_APPLICATION_CREDENTIALS`` — for ``vertex_ai/...`` (GCP service account)

    When none of these are set, the audit pipeline skips the LLM call entirely
    and uses the deterministic executive-summary template. This keeps the OSS
    shipped default quiet (no LiteLLM provider-probe warnings) for users who
    just want the structured-evidence audit and don't need a generated prose
    summary. To unlock LLM summaries, set one of those env vars (see README).
    """
    import os as _os

    return any(
        _os.environ.get(k)
        for k in (
            "GEMINI_API_KEY",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
        )
    )


async def generate_executive_summary(
    audit_result: AuditResult,
    wiki_pages: list[WikiPage],
    variant: ReportVariant = "compliance",
    recovery: dict[str, int | float | str | bool] | None = None,
) -> str:
    """Generate LLM-written executive summary grounded in wiki regulatory context.

    Uses the configured classify model when an LLM provider API key is present
    in the environment. When no key is configured (the OSS-default state), the
    function skips the LLM call entirely — no LiteLLM warnings, no Vertex /
    Bedrock / SageMaker probe noise — and returns the deterministic template
    summary directly. See ``_llm_key_available()`` for the exact env vars
    checked and the README for the setup instructions.
    """
    if _llm_key_available():
        try:
            settings = get_settings()
            client = LLMClient(model=settings.default_classify_model)
            prompt = _build_executive_summary_prompt(audit_result, wiki_pages, variant, recovery)
            response = await client.complete(messages=[{"role": "user", "content": prompt}])
            return str(response["choices"][0]["message"]["content"])
        except Exception:  # noqa: BLE001
            pass  # fall through to deterministic summary below

    # Deterministic summary path — no LLM, no warnings. Used when the user has
    # not configured any LLM API key (the OSS-default shipping state).
    violations = [f.vendor.name for f in _confirmed_violations(audit_result)]
    if variant == "signal":
        if violations:
            rec_suffix = ""
            if recovery and recovery.get("has_recovery_opportunity"):
                rec_suffix = (
                    f" Estimated recoverable ad revenue at current spend: "
                    f"${recovery['monthly_recoverable_low_usd']:,}-${recovery['monthly_recoverable_high_usd']:,}/mo."
                )
            return (
                f"Signal gaps detected at {audit_result.url}. "
                f"The following vendors are leaking post-consent data the ad AI cannot optimize on: "
                f"{', '.join(violations)}. "
                f"This caps scale on Meta Advantage+, Performance Max, and TikTok Smart+ — "
                f"the ad platforms optimize on the signal they receive, and this stack is giving them an incomplete picture."
                f"{rec_suffix}"
            )
        return (
            f"No consent-driven signal gaps detected at {audit_result.url} "
            f"under the {audit_result.methodology} methodology. "
            f"The measurement stack is AI-ready — ad platforms are receiving clean post-consent signal."
        )
    if violations:
        jurisdiction = audit_result.detected_jurisdiction or "US"
        law = "CCPA/CPRA" if jurisdiction in ("US", "CA") else "GDPR"
        return (
            f"Confirmed consent violations detected at {audit_result.url}. "
            f"The following vendors fired tracking technologies despite opted-out consent: "
            f"{', '.join(violations)}. "
            f"This constitutes a potential violation of {law} and may expose the organization "
            f"to regulatory enforcement and class-action litigation."
        )
    return (
        f"No confirmed consent violations were detected at {audit_result.url} "
        f"under the {audit_result.methodology} methodology."
    )


def _build_manual_validation(audit_result: AuditResult) -> list[dict[str, str]]:
    """Build scenario-specific manual validation steps based on audit findings.

    Each step has: title, what (what to check), how (browser steps), expect (what confirms/denies).
    Only includes steps relevant to what this specific audit found.
    """
    steps: list[dict[str, str]] = []
    violations = _confirmed_violations(audit_result)
    pixel_violations = [p for p in audit_result.pixel_firings if not p.is_acm_ping]
    pixel_acm_pings = [p for p in audit_result.pixel_firings if p.is_acm_ping]
    gcs_state = audit_result.gcs_value.raw if audit_result.gcs_value else None
    gcs_full_denial = bool(
        gcs_state and len(gcs_state) >= 4 and gcs_state[2] == "0" and gcs_state[3] == "0"
    )
    gcs_partial = bool(
        gcs_state and len(gcs_state) >= 4 and "0" in gcs_state[2:] and not gcs_full_denial
    )
    gcs_cmp_broken = bool(
        gcs_state
        and audit_result.methodology
        in (MethodologyFlag.S3, MethodologyFlag.S3_CONSENT_WIRING_BROKEN)
        and len(gcs_state) >= 4
        and "0" not in gcs_state[2:]
    )

    # 1. Always: verify CMP banner appears
    cmp_name = audit_result.detected_cmp or "consent banner"
    steps.append(
        {
            "title": "CMP Banner Presence",
            "what": f"Verify {cmp_name} appears for California visitors.",
            "how": (
                "Open an incognito window. Use a VPN set to Los Angeles, CA (or Chrome DevTools > "
                "Sensors > Location: Los Angeles). Navigate to the site. The consent banner should "
                "appear on first visit."
            ),
            "expect": (
                f"Banner appears with Reject/Deny option. "
                f"{'Our scan detected ' + cmp_name + ' via cookie injection.' if audit_result.cmp_interaction_method and 'injection' in (audit_result.cmp_interaction_method or '') else ''}"
                f"{'Our scan did NOT see a visible banner. The CMP may be IP-gated to specific regions.' if not audit_result.detected_cmp else ''}"
            ),
        }
    )

    # 2. If violations: verify each violating vendor's cookies post-opt-out
    if violations:
        vendor_names = [f.vendor.name for f in violations[:6]]
        cookie_names = []
        for f in violations[:6]:
            cookie_names.extend(f.cookies_observed[:2])
        steps.append(
            {
                "title": "Cookie Persistence After Opt-Out",
                "what": f"Confirm violating vendor cookies persist after clicking Reject All: {', '.join(vendor_names)}.",
                "how": (
                    "In incognito (CA VPN): (1) Navigate to site, (2) Click 'Reject All' or equivalent, "
                    "(3) Open DevTools > Application > Cookies, (4) Search for: "
                    f"{', '.join(cookie_names[:6])}. "
                    "Reload the page and check again."
                ),
                "expect": (
                    "If cookies from these vendors are present after opt-out, the violation is confirmed. "
                    "If cookies are cleared on reject but reappear after reload, the CMP clears cookies but "
                    "tags re-fire them on the next page load (still a violation)."
                ),
            }
        )

    # 3. If GCS detected: verify Consent Mode state
    if gcs_state:
        if gcs_cmp_broken:
            steps.append(
                {
                    "title": f"Consent Mode Integration (GCS={gcs_state})",
                    "what": "Verify CMP is NOT updating Google Consent Mode on opt-out.",
                    "how": (
                        "In incognito (CA VPN): (1) Navigate to site, (2) Open DevTools > Console, "
                        "(3) Click Reject All, (4) Run: "
                        "document.cookie.split(';').find(c => c.trim().startsWith('GCS=')) "
                        "or check Network tab for any google request containing 'gcs=' parameter. "
                        "Also check: dataLayer.push events for 'consent' or 'update'."
                    ),
                    "expect": (
                        f"Our scan found GCS={gcs_state} (both granted) AFTER opt-out. "
                        "If you see the same, the CMP is not propagating consent denial to Google tags. "
                        "Expected correct value after opt-out: G100 (both denied)."
                    ),
                }
            )
        elif gcs_full_denial:
            steps.append(
                {
                    "title": f"Consent Mode Verification (GCS={gcs_state})",
                    "what": "Confirm Advanced Consent Mode is correctly denying post-opt-out.",
                    "how": (
                        "In incognito (CA VPN): (1) Navigate to site, (2) Click Reject All, "
                        "(3) Open DevTools > Network, filter by 'google', "
                        "(4) Look for requests to google-analytics.com or googleads.g.doubleclick.net "
                        "and check the 'gcs=' query parameter."
                    ),
                    "expect": (
                        "GCS=G100 (both denied). You may still see Google network requests. This is "
                        "expected ACM behavior: cookieless modeling pings with npa=1. No cookie IDs "
                        "should be transmitted. This is compliant."
                    ),
                }
            )
        elif gcs_partial:
            _p_ad = gcs_state[2] == "0" if len(gcs_state) >= 3 else False
            _p_desc = (
                "ad_storage denied but analytics_storage still granted"
                if _p_ad
                else "analytics_storage denied but ad_storage still granted"
            )
            steps.append(
                {
                    "title": f"Partial Consent Mode (GCS={gcs_state})",
                    "what": f"Verify partial opt-out: {_p_desc}.",
                    "how": (
                        "In incognito (CA VPN): (1) Navigate to site, (2) Click Reject All, "
                        "(3) DevTools > Network > filter 'google' > check 'gcs=' parameter. "
                        "(4) Also check if GA4 requests still fire with full measurement_id."
                    ),
                    "expect": (
                        f"GCS={gcs_state} confirms partial denial only. Under CCPA, 'Do Not Sell' "
                        "must halt ALL data sharing for advertising AND analytics profiling. "
                        "A compliant state would be G100 (both denied)."
                    ),
                }
            )

    # 4. If pixel violations: verify network-level pixel firing
    if pixel_violations:
        top_pixels = pixel_violations[:4]
        patterns = [p.matched_pattern for p in top_pixels]
        steps.append(
            {
                "title": "Network Pixel Firing Post-Denial",
                "what": f"Verify tracking pixels fire after opt-out: {', '.join(p.vendor_name for p in top_pixels)}.",
                "how": (
                    "In incognito (CA VPN): (1) Navigate to site, (2) Open DevTools > Network, "
                    "(3) Click Reject All, (4) Reload page, (5) Filter network requests for: "
                    f"{', '.join(patterns)}. "
                    "Look for outbound requests to these domains/paths."
                ),
                "expect": (
                    "If these requests appear in network traffic after clicking Reject All, "
                    "the pixels are firing despite consent denial. Each request is independent "
                    "forensic evidence (this is the plaintiff law firm methodology for CIPA claims)."
                ),
            }
        )

    # 5. If ACM pings detected: explain expected behavior
    if pixel_acm_pings:
        steps.append(
            {
                "title": "ACM Cookieless Pings (Expected Behavior)",
                "what": "Verify Google pings are cookieless modeling pings, not violations.",
                "how": (
                    "In DevTools > Network, after opt-out, filter for google-analytics.com requests. "
                    "Click on a request and check query parameters for: gcs=G100, npa=1. "
                    "Also verify no _ga or _gid cookie values appear in the Cookie header."
                ),
                "expect": (
                    "Requests with gcs=G100 + npa=1 and NO cookie IDs = correct ACM behavior. "
                    "Google uses these for cookieless conversion modeling. This is NOT a violation."
                ),
            }
        )

    # 6. If SSGTM detected: server-side verification
    if audit_result.ssgtm_detected:
        steps.append(
            {
                "title": f"Server-Side GTM ({audit_result.ssgtm_domain})",
                "what": "Verify server-side container is proxying requests.",
                "how": (
                    f"In DevTools > Network, look for requests to {audit_result.ssgtm_domain}. "
                    "These may appear as first-party requests (same domain or subdomain). "
                    "Check if the response sets cookies or forwards data to third parties. "
                    "Also check: does the SSGTM domain appear in DNS as a CNAME to googletagmanager.com?"
                ),
                "expect": (
                    "Server-side GTM containers cannot be blocked by client-side consent enforcement. "
                    "If SSGTM is forwarding user data to ad platforms post-opt-out, this is a consent "
                    "bypass that requires server-side consent logic (not detectable from client-side)."
                ),
            }
        )

    # 7. If GPC tested: verify GPC signal handling
    if audit_result.gpc_tested:
        steps.append(
            {
                "title": "GPC Signal (Sec-GPC: 1)",
                "what": "Verify the site respects the Global Privacy Control signal.",
                "how": (
                    "Install a GPC browser extension (e.g., OptMeowt or Privacy Badger with GPC enabled). "
                    "Navigate to the site. Check: (1) Does the CMP auto-set to opt-out? "
                    "(2) In DevTools > Network, do request headers include 'Sec-GPC: 1'? "
                    "(3) Does navigator.globalPrivacyControl return true in Console?"
                ),
                "expect": (
                    "Under CCPA/CPRA, GPC is a legally binding opt-out signal. The CMP should auto-deny "
                    "consent when GPC is detected. California's CPPA has stated GPC non-compliance is "
                    "enforceable without prior notice."
                ),
            }
        )

    # 8. If GTM container was extracted: verify tag consent settings
    if audit_result.tag_consent_map:
        missing_consent = [t for t in audit_result.tag_consent_map if t.requirement == "missing"]
        if missing_consent:
            tag_names = [t.tag_name for t in missing_consent[:4]]
            steps.append(
                {
                    "title": "GTM Tags Missing Consent Configuration",
                    "what": f"Verify these tags lack built-in consent checks: {', '.join(tag_names)}.",
                    "how": (
                        "Open GTM workspace > Tags. For each tag listed, check: "
                        "(1) Does it have a 'Consent' section? "
                        "(2) Is 'Require additional consent for tag to fire' enabled? "
                        "(3) Are the correct consent types (ad_storage, analytics_storage) configured? "
                        "Also check if the tag has a consent-aware trigger (e.g., fires only when "
                        "OnetrustActiveGroups contains the correct category)."
                    ),
                    "expect": (
                        "Tags without consent configuration will fire regardless of user consent state. "
                        "Each must have either built-in consent checks or consent-aware triggers."
                    ),
                }
            )

    return steps


async def generate_report(
    audit_result: AuditResult,
    wiki_pages: list[WikiPage],
    executive_summary: str,
    report_variant: ReportVariant = "compliance",
    estimated_monthly_ad_spend_usd: int | None = None,
    firm_name: str | None = None,
) -> str:
    """Render AuditResult as a self-contained HTML audit report.

    Args:
        audit_result: Fully populated AuditResult from the audit pipeline.
        wiki_pages: Regulatory wiki pages from Tool 7.
        executive_summary: LLM-written prose from generate_executive_summary().
        report_variant:
          - "compliance" (default): legal/risk framing for privacy buyer (existing behavior)
          - "signal": growth/scale framing for CMO buyer; adds recoverable-revenue block
        estimated_monthly_ad_spend_usd: optional buyer-reported monthly ad spend.
          Only used when ``report_variant == "signal"``. Defaults to ICP anchor when omitted.

    Returns:
        Self-contained HTML string (inline CSS, no external dependencies).
    """
    env = _get_jinja_env()
    template = env.get_template("audit_report.html.j2")

    findings_with_violations = _confirmed_violations(audit_result)

    validation_steps = _build_manual_validation(audit_result)

    recovery = (
        estimate_recoverable_revenue(audit_result, estimated_monthly_ad_spend_usd)
        if report_variant == "signal"
        else None
    )

    exposure = estimate_exposure_usd(audit_result) if report_variant == "compliance" else None

    html: str = template.render(
        result=audit_result,
        executive_summary=executive_summary,
        wiki_pages=wiki_pages,
        findings_with_violations=findings_with_violations,
        validation_steps=validation_steps,
        methodology_label=_METHODOLOGY_LABELS.get(
            audit_result.methodology, audit_result.methodology
        ),
        report_variant=report_variant,
        recovery=recovery,
        exposure=exposure,
        firm_name=firm_name,
    )
    return html


def _slide_summary(text: str, max_sentences: int = 2, max_vendors: int = 6) -> str:
    """Truncate full exec summary to fit on a slide (2 sentences max).

    Also collapses long vendor enumerations: if a sentence lists more than
    ``max_vendors`` vendors, keep the first ``max_vendors`` and append
    "... and N more" so a 30+ vendor list doesn't push the verdict cards
    off the slide.
    """
    import re as _re

    sentences = [s.strip() for s in text.replace(".\n", ". ").split(". ") if s.strip()]
    kept = sentences[:max_sentences]

    # Collapse long vendor lists per sentence.
    # Heuristic: if a sentence contains a colon-introduced list with many commas,
    # trim to the top N entries. Matches "...: A, B, C, D, E, F, G, H." patterns.
    trimmed: list[str] = []
    for s in kept:
        m = _re.match(r"^(.*?:\s*)(.+)$", s)
        if not m:
            trimmed.append(s)
            continue
        prefix, tail = m.group(1), m.group(2)
        # Only treat as a list if separated by commas with many items
        parts = [p.strip() for p in tail.split(",") if p.strip()]
        if len(parts) > max_vendors:
            more = len(parts) - max_vendors
            trimmed.append(f"{prefix}{', '.join(parts[:max_vendors])}, and {more} more")
        else:
            trimmed.append(s)

    result = ". ".join(trimmed)
    if not result.endswith("."):
        result += "."
    return result


def generate_marp_slides(
    audit_result: AuditResult,
    executive_summary: str,
    site_image_url: str | None = None,
    brand: str = "rsc",
    firm_name: str | None = None,
    report_variant: str = "compliance",
    estimated_monthly_ad_spend_usd: int | None = None,
) -> str:
    """Generate a Marp-compatible markdown presentation from an audit result.

    Marp (https://marp.app) renders markdown as slides. The output can be
    converted to PDF, PPTX, or HTML for client delivery.

    Args:
        audit_result: Fully populated AuditResult.
        executive_summary: LLM-written executive summary from generate_executive_summary().
        site_image_url: OG image or favicon URL to display on title slide. None = globe SVG.

    Returns:
        Marp markdown string. Save as .md and open with Marp CLI or VS Code Marp extension.
    """
    violations = _confirmed_violations(audit_result)
    pixel_firings = audit_result.pixel_firings
    # Separate real violations from ACM pings — pings are expected behavior, not evidence
    pixel_violations = [p for p in pixel_firings if not p.is_acm_ping]
    pixel_acm_pings = [p for p in pixel_firings if p.is_acm_ping]
    clean = not violations and not pixel_violations
    jurisdiction = audit_result.detected_jurisdiction or "US"
    gcs_state = audit_result.gcs_value.raw if audit_result.gcs_value else None
    # GCS interpretation: in an opt-out test (S3):
    #   G100 = both denied (full ACM compliance)
    #   G101 = ad denied, analytics granted (partial opt-out — ads only)
    #   G110 = analytics denied, ad granted (partial opt-out — analytics only)
    #   G111 = both granted (CMP integration failure)
    _gcs_any_denial = bool(gcs_state and len(gcs_state) >= 4 and "0" in gcs_state[2:])
    _gcs_full_denial = bool(
        gcs_state and len(gcs_state) >= 4 and gcs_state[2] == "0" and gcs_state[3] == "0"
    )
    _gcs_partial = _gcs_any_denial and not _gcs_full_denial  # e.g. G101
    _gcs_cmp_broken = bool(
        gcs_state
        and audit_result.methodology
        in (MethodologyFlag.S3, MethodologyFlag.S3_CONSENT_WIRING_BROKEN)
        and len(gcs_state) >= 4
        and "0" not in gcs_state[2:]  # Granted/unset state during opt-out test
    )
    url_display = audit_result.url.replace("https://", "").replace("http://", "").rstrip("/")

    # Applicable law slide content
    if jurisdiction == "EU":
        law_content = (
            "- **GDPR Art. 6(1)(a)**: Consent required for behavioral advertising cookies\n"
            "- **ePrivacy Directive Art. 5(3)**: Prior consent for any non-essential cookie\n"
            "- **Legitimate interest**: Rejected by EU regulators for ad profiling (LinkedIn €310M)\n"
            "- **Max fine**: 4% of global revenue or €20M, whichever is higher"
        )
    else:
        law_content = (
            "- **CCPA/CPRA §1798.120**: Right to opt out of sale and sharing\n"
            "- **CPRA sharing extension**: Covers pixel-based data transfer to ad platforms\n"
            "- **GPC mandate**: `Sec-GPC: 1` is a legally binding opt-out signal\n"
            "- **Fine exposure**: Up to $7,500 per intentional violation per consumer\n"
            "- **CIPA**: $5,000 statutory per-violation — no actual damages required"
        )

    methodology_label = _METHODOLOGY_LABELS.get(
        audit_result.methodology, str(audit_result.methodology)
    )

    # Pre-compute law items HTML (avoids backslash-in-f-string issues)
    _law_item_style = (
        "display:flex;gap:12px;align-items:flex-start;padding:10px 0;"
        "border-bottom:1px solid #e7e3d8;font-size:0.75em;"
    )
    _law_label_style = "color:#4b5563;font-weight:600;font-family:'Inter';min-width:10px;"
    _law_text_style = "color:#9ca3af;font-weight:200;line-height:1.6;"
    _law_items_html_parts = []
    for _law_line in law_content.strip().splitlines():
        if _law_line.strip().startswith("-"):
            _law_text = _law_line.lstrip("- ").replace("**", "").strip()
            _law_items_html_parts.append(
                f'<div style="{_law_item_style}">'
                f'<div style="{_law_label_style}">—</div>'
                f'<div style="{_law_text_style}">{_law_text}</div>'
                f"</div>"
            )
    _law_items_html = "".join(_law_items_html_parts)

    # Pre-compute action slide colors/labels (panel computed after _actions_30d_html is built)
    _action_color = "#ef4444" if violations else "#22c55e"
    _action_label = "Immediate" if violations else "Ongoing"
    _action_panel_style = f"flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:3px solid {_action_color};"
    _action_hdr_style = f"font-family:'Inter';font-weight:600;font-size:0.62em;color:{_action_color};text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;"

    # ── HTML component builders ──────────────────────────────────────────────
    # SVG check / X / dash / warning icons (inline, render with --html flag)
    _SVG_CHECK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
    _SVG_CROSS = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    _SVG_WARN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
    _SVG_DASH = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>'

    def _tag(label: str, color: str, bg_alpha: str = "12") -> str:
        return (
            f"<span style=\"font-family:'Inter';font-weight:600;font-size:0.55em;"
            f"letter-spacing:0.12em;text-transform:uppercase;padding:3px 10px;"
            f"border-radius:4px;background:{color}{bg_alpha};color:{color};"
            f'border:1px solid {color}22;">{label}</span>'
        )

    def _metric_card(label: str, value: str, sub: str, accent: str) -> str:
        # Top-row card. Sized to align visually with the bottom-row scenario
        # cards on the financial-exposure slide — matching padding + flex base
        # so the two rows render at equal heights regardless of value width.
        return (
            f'<div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;'
            f'padding:12px 14px;border-top:3px solid {accent};">'
            f'<div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;'
            f"letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;\">{label}</div>"
            f"<div style=\"font-family:'Inter';font-weight:800;font-size:1.7em;color:{accent};"
            f'line-height:1.1;margin-bottom:4px;letter-spacing:-0.01em;">{value}</div>'
            f'<div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">{sub}</div>'
            f"</div>"
        )

    def _findings_row(label: str, value: str, icon: str) -> str:
        return (
            f'<div style="display:flex;align-items:center;padding:11px 0;'
            f'border-bottom:1px solid #e7e3d8;font-size:0.75em;">'
            f'<div style="flex:2.5;color:#6b7280;font-weight:200;">{label}</div>'
            f'<div style="flex:3;color:#d1d5db;font-weight:400;">{value}</div>'
            f'<div style="flex:0 0 28px;text-align:center;">{icon}</div>'
            f"</div>"
        )

    def _vendor_card(name: str, cookies: str, category: str, exposure: str) -> str:
        e_color = (
            "#ef4444" if exposure == "high" else "#f59e0b" if exposure == "medium" else "#6b7280"
        )
        e_label = (
            "HIGH RISK"
            if exposure == "high"
            else "MEDIUM RISK"
            if exposure == "medium"
            else exposure.upper()
        )
        return (
            f'<div style="flex:1;min-width:160px;background:#ffffff;border-radius:10px;'
            f'padding:16px;border-left:3px solid {e_color};">'
            f"<div style=\"font-family:'Inter';font-weight:600;font-size:0.82em;"
            f'color:#14182b;margin-bottom:6px;">{name}</div>'
            f'<div style="color:#4b5563;font-size:0.62em;margin-bottom:10px;'
            f"font-family:'Inter';\">{cookies}</div>"
            f"{_tag(e_label, e_color)}"
            f"</div>"
        )

    def _pixel_row(vendor: str, pattern: str, category: str, exposure: str) -> str:
        e_color = "#ef4444" if exposure == "high" else "#f59e0b"
        return (
            f'<div style="display:flex;align-items:center;padding:10px 0;'
            f'border-bottom:1px solid #e7e3d8;font-size:0.73em;">'
            f'<div style="flex:2;color:#d1d5db;font-weight:400;font-family:\'Outfit\';font-weight:600;">{vendor}</div>'
            f'<div style="flex:3;color:#4b5563;font-family:\'SF Mono\',monospace;font-size:0.9em;">{pattern}</div>'
            f'<div style="flex:1.5;">{_tag(category.replace("_"," "), e_color)}</div>'
            f'</div>'
        )

    # ── Build component HTML ─────────────────────────────────────────────────

    # Verdict metric cards
    v_count = len(violations)
    p_count = len(pixel_violations)
    _verdict_cards = '<div style="display:flex;gap:10px;margin-top:22px;">'
    _verdict_cards += _metric_card(
        "Cookie Violations",
        str(v_count) if v_count else "0",
        "confirmed vendors" if v_count else "none detected",
        "#ef4444" if v_count else "#22c55e",
    )
    _verdict_cards += _metric_card(
        "Pixel Endpoints",
        str(p_count) if p_count else "0",
        "post-denial firings" if p_count else "none detected",
        "#ef4444" if p_count else "#22c55e",
    )
    _verdict_cards += _metric_card(
        "GCS State",
        gcs_state or "N/A",
        "ACM correct — cookieless only"
        if _gcs_full_denial
        else (
            (
                "Partial opt-out — ads denied, analytics active"
                if (
                    gcs_state
                    and len(gcs_state) >= 4
                    and gcs_state[2] == "0"
                    and gcs_state[3] == "1"
                )
                else "Partial opt-out — analytics denied, ads active"
                if (
                    gcs_state
                    and len(gcs_state) >= 4
                    and gcs_state[2] == "1"
                    and gcs_state[3] == "0"
                )
                else "Partial opt-out"
            )
            if _gcs_partial
            else ("CMP integration failure" if _gcs_cmp_broken else "not detected")
        ),
        "#22c55e"
        if _gcs_full_denial
        else ("#f59e0b" if (_gcs_partial or _gcs_cmp_broken) else "#3d6abb"),
    )
    _verdict_cards += _metric_card(
        "Jurisdiction", jurisdiction, "simulated: Los Angeles, CA", "#3d6abb"
    )
    _verdict_cards += "</div>"

    # Findings comparison rows
    _fr = '<div style="margin-top:14px;">'
    _fr += _findings_row(
        "Cookie Violations",
        f"<strong style='color:#ef4444'>{v_count} confirmed vendor{'s' if v_count!=1 else ''}</strong>"
        if violations
        else "None detected",
        _SVG_CROSS if violations else _SVG_CHECK,
    )
    _fr += _findings_row(
        "Network Pixel Endpoints",
        f"<strong style='color:#ef4444'>{p_count} post-denial endpoint{'s' if p_count!=1 else ''}</strong>"
        if pixel_violations
        else "None detected",
        _SVG_CROSS if pixel_violations else _SVG_CHECK,
    )
    _gcs_code = (
        f"<code style='background:#faf8f2;color:#14182b;border:1px solid #e7e3d8;"
        f"padding:2px 8px;border-radius:3px;font-size:0.9em;"
        f"font-family:\"SF Mono\",Menlo,monospace;font-weight:600;'>{gcs_state}</code>"
    )
    if _gcs_full_denial:
        _gcs_display = f"{_gcs_code} — ACM implemented correctly (cookieless pings only)"
        _gcs_icon = _SVG_CHECK
    elif _gcs_partial:
        _p_ad = gcs_state and len(gcs_state) >= 3 and gcs_state[2] == "0"
        _p_analytics = gcs_state and len(gcs_state) >= 4 and gcs_state[3] == "0"
        _p_label = (
            "ad_storage denied, analytics_storage still granted"
            if _p_ad and not _p_analytics
            else "analytics_storage denied, ad_storage still granted"
            if _p_analytics and not _p_ad
            else "partial denial"
        )
        _gcs_display = f"{_gcs_code} — Partial opt-out: {_p_label}"
        _gcs_icon = _SVG_WARN
    elif _gcs_cmp_broken:
        _gcs_display = (
            f"{_gcs_code} — CMP not updating Consent Mode on opt-out (integration failure)"
        )
        _gcs_icon = _SVG_WARN
    else:
        _gcs_display = gcs_state or "Not detected"
        _gcs_icon = _SVG_DASH
    _fr += _findings_row("Consent Mode (GCS)", _gcs_display, _gcs_icon)
    _fr += _findings_row(
        "Server-Side GTM",
        f"<strong style='color:#f59e0b'>{audit_result.ssgtm_domain}</strong> — consent bypass risk"
        if audit_result.ssgtm_detected
        else "Not detected",
        _SVG_WARN if audit_result.ssgtm_detected else _SVG_DASH,
    )
    _fr += _findings_row(
        "CMP Detected",
        audit_result.detected_cmp or "Not detected",
        _SVG_CHECK if audit_result.detected_cmp else _SVG_DASH,
    )
    _fr += _findings_row(
        "GPC Signal Honored",
        "Tested — mandatory opt-out signal sent" if audit_result.gpc_tested else "Not tested",
        (_SVG_CROSS if violations else _SVG_CHECK) if audit_result.gpc_tested else _SVG_DASH,
    )
    _fr += "</div>"

    # Vendor violation cards — max 4 per slide, worst violators first
    _MAX_VENDOR_CARDS = 4
    _EXPOSURE_ORDER = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    _sorted_violations = sorted(
        violations, key=lambda f: _EXPOSURE_ORDER.get(f.vendor.legal_exposure.value, 3)
    )
    _vendor_cards_html = ""
    if _sorted_violations:
        _vendor_cards_html = '<div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;">'
        for f in _sorted_violations[:_MAX_VENDOR_CARDS]:
            cookies_str = ", ".join(f.cookies_observed[:3]) or "—"
            _vendor_cards_html += _vendor_card(
                f.vendor.name, cookies_str, f.vendor.category.value, f.vendor.legal_exposure.value
            )
        _vendor_cards_html += "</div>"
        if len(_sorted_violations) > _MAX_VENDOR_CARDS:
            _vendor_cards_html += (
                f'<p style="font-size:0.65em;color:#4b5563;margin-top:6px;">'
                f"+{len(_sorted_violations) - _MAX_VENDOR_CARDS} additional vendors documented in full report</p>"
            )

    # Pixel evidence rows — violations only; ACM pings shown separately as observations
    # Split into pages of 5 rows to avoid Marp slide overflow
    _MAX_PIXEL_ROWS_PER_SLIDE = 5
    _pixel_slides: list[str] = []
    if pixel_violations:
        for i in range(0, len(pixel_violations), _MAX_PIXEL_ROWS_PER_SLIDE):
            chunk = pixel_violations[i : i + _MAX_PIXEL_ROWS_PER_SLIDE]
            slide_html = '<div style="margin-top:14px;">'
            for pf in chunk:
                slide_html += _pixel_row(
                    pf.vendor_name, pf.matched_pattern, pf.category, pf.legal_exposure
                )
            slide_html += "</div>"
            if i > 0:
                slide_html += f'<p style="font-size:0.6em;color:#4b5563;margin-top:8px;">Continued ({i + 1}–{i + len(chunk)} of {len(pixel_violations)})</p>'
            _pixel_slides.append(slide_html)
    # ACM observation on its own slide if there are also pixel violations,
    # otherwise append to the first (and only) pixel slide
    _acm_block = ""
    if pixel_acm_pings:
        _acm_block = (
            '<div style="margin-top:12px;background:#ffffff;border-radius:8px;padding:12px 16px;'
            'border-left:3px solid #22c55e;">'
            "<div style=\"font-family:'Inter';font-weight:600;font-size:0.62em;color:#22c55e;"
            'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Observation — Expected ACM Behavior</div>'
            '<div style="font-size:0.68em;color:#6b7280;line-height:1.6;">'
        )
        for pf in pixel_acm_pings:
            _acm_block += (
                f'<div><strong style="color:#9ca3af;">{pf.vendor_name}</strong> '
                f'<span style="color:#4b5563;">({pf.matched_pattern})</span> — '
                f"Consent Mode cookieless ping (GCS=G100, npa=1). "
                f"No cookie ID transmitted. This is correct Advanced Consent Mode behavior.</div>"
            )
        _acm_block += "</div></div>"
    # If only one pixel slide and ACM fits, combine them; otherwise ACM gets its own slide
    if _pixel_slides and len(pixel_violations) <= _MAX_PIXEL_ROWS_PER_SLIDE:
        _pixel_slides[0] += _acm_block
    elif _acm_block:
        _pixel_slides.append(_acm_block)

    # Build complete Marp section for all pixel slides (proper --- separators)
    _pixel_marp_section = ""
    if _pixel_slides:
        parts = []
        for i, slide in enumerate(_pixel_slides):
            if i > 0:
                header = f"### NETWORK EVIDENCE\n\n# Pixel Endpoints (cont. {i + 1})"
            else:
                header = "### NETWORK EVIDENCE\n\n# Post-Denial Pixel Endpoints"
            subtitle = (
                (
                    '\n\n<p style="font-size:0.75em;color:#9ca3af;margin-bottom:4px;">'
                    "Primary exhibit methodology used by plaintiff law firms "
                    "(CIPA §631 · CCPA class actions)</p>\n"
                )
                if i == 0
                else "\n"
            )
            parts.append(header + subtitle + slide)
        _pixel_marp_section = "\n\n---\n\n".join(parts)

    # Financial exposure — statutory rates + realistic brand extrapolation
    _exposure_html = ""
    if violations or pixel_violations:
        v_count = len(violations)
        p_count = len(pixel_violations)
        # Statutory rates row — top of slide
        _exposure_html = '<div style="display:flex;gap:8px;margin-top:14px;align-items:stretch;">'
        _exposure_html += _metric_card(
            "CCPA / CPRA", "$7,500", "per intentional violation · per consumer", "#3d6abb"
        )
        _exposure_html += _metric_card(
            "CIPA §631", "$5,000", "per session · no actual damages required", "#3d6abb"
        )
        _exposure_html += _metric_card(
            "FTC Act", "$51,744", "per day of ongoing violation", "#3d6abb"
        )
        _exposure_html += "</div>"

        # Realistic exposure extrapolation — 3 traffic tiers
        # Conservative (50K CA opt-outs/mo), Mid (250K), High (1M) — client self-selects tier
        _scenarios = []
        for label, ca_optouts_mo in [
            ("Conservative", 50_000),
            ("Mid-range", 250_000),
            ("High-traffic", 1_000_000),
        ]:
            ccpa_annual = ca_optouts_mo * 12 * v_count * 7_500
            cipa_annual = ca_optouts_mo * 12 * 5_000
            # Realistic settlement = 0.01%–0.1% of theoretical statutory max (based on precedents)
            settlement_low = int((ccpa_annual + cipa_annual) * 0.0001)
            settlement_high = int((ccpa_annual + cipa_annual) * 0.001)
            _scenarios.append(
                (label, ca_optouts_mo, ccpa_annual + cipa_annual, settlement_low, settlement_high)
            )

        def _fmt(n: int) -> str:
            if n >= 1_000_000_000:
                return f"${n/1_000_000_000:.1f}B"
            if n >= 1_000_000:
                return f"${n/1_000_000:.1f}M"
            return f"${n/1_000:.0f}K"

        # Scenario cards — bottom row. Equal width via flex:1 1 0, min-width:0
        # so wide ranges can shrink inside their column instead of pushing the
        # row past the slide bounds. Smaller value font (1.05em) matches the
        # top-row card hierarchy and stays on one line at any tier.
        _exposure_html += '<div style="display:flex;gap:8px;margin-top:8px;align-items:stretch;">'
        for label, optouts, statutory, s_low, s_high in _scenarios:
            _exposure_html += (
                f'<div style="flex:1 1 0;min-width:0;background:#ffffff;border-radius:10px;'
                f'padding:12px 14px;border-top:3px solid #ef4444;">'
                f'<div style="color:#4b5563;font-size:0.55em;text-transform:uppercase;'
                f"letter-spacing:0.14em;margin-bottom:4px;font-family:'Inter';font-weight:600;\">{label}</div>"
                f"<div style=\"font-family:'Inter';font-weight:800;font-size:1.05em;color:#ef4444;"
                f'line-height:1.15;margin-bottom:4px;letter-spacing:-0.01em;">'
                f"{_fmt(s_low)}–{_fmt(s_high)}</div>"
                f'<div style="color:#6b7280;font-size:0.55em;font-weight:300;line-height:1.45;">'
                f"{optouts:,} CA opt-outs/mo<br>max {_fmt(statutory)}/yr</div>"
                f"</div>"
            )
        _exposure_html += "</div>"

        # Benchmarks footnote — matches existing panel style
        _exposure_html += (
            '<div style="margin-top:8px;background:#ffffff;border-radius:8px;padding:8px 14px;'
            'border-left:3px solid #374151;">'
            '<div style="font-size:0.6em;color:#4b5563;line-height:1.5;">'
            "Realistic settlement range calibrated to precedent: "
            "Sephora $1.2M (2022) · Tractor Supply $1.35M (Sep 2025) · Disney $2.75M (Feb 2026)"
            "</div></div>"
        )

    # CMP Self-Report slide — what the CMP says about itself via its JS API.
    # Renders only when the introspector got a hit (template + geolocation).
    _cmp_runtime_slide_md = ""
    _rc = audit_result.cmp_runtime_config
    if _rc and (_rc.template_name or _rc.geolocation_rule):
        _rc_rows = [
            ("CMP", _rc.cmp_name),
        ]
        if _rc.template_name:
            _rc_rows.append(("Template", _rc.template_name))
        if _rc.geolocation_rule:
            _rc_rows.append(("Geo Rule", _rc.geolocation_rule))
        if _rc.geolocation_country:
            _rc_rows.append(("Geo Country", _rc.geolocation_country))
        _rc_rows.append(("Consent Model", _rc.consent_model.capitalize()))
        if _rc.script_version:
            _rc_rows.append(("Script Version", _rc.script_version))
        _rc_rows_html = "\n".join(
            f"  <tr><td style='padding:6px 14px;color:#4b5563;font-weight:600;'>{k}</td>"
            f"<td style='padding:6px 14px;color:#14182b;'>{v}</td></tr>"
            for k, v in _rc_rows
        )
        _cmp_runtime_slide_md = (
            "---\n\n"
            "<!-- _class: compact -->\n\n"
            "### CMP SELF-REPORT · GROUND TRUTH\n\n"
            "# What the CMP Says It Does\n\n"
            "<p style='font-size:0.42em;color:#4b5563;margin-top:-6px;'>"
            "Captured directly from the CMP's JavaScript API during the scan. "
            "This is the configuration the CMP <em>believes</em> it is enforcing. "
            "Compare against the observed network behavior below to surface "
            "misconfigurations.</p>\n\n"
            "<table style='border-collapse:collapse;font-size:0.5em;margin-top:12px;'>"
            "<tbody>\n"
            f"{_rc_rows_html}\n"
            "</tbody></table>\n"
        )

    # GPC Compliance slide — dedicated evidence block for screenshot sharing
    _gpc_slide_md = ""
    if audit_result.gpc_tested:
        _gpc_respected = audit_result.gpc_signal_respected
        if _gpc_respected is True:
            _gpc_verdict_label = "Respected"
            _gpc_verdict_color = "#22c55e"
            _gpc_honored_text = (
                "<strong style='color:#22c55e'>YES</strong> — tracking pixels stopped "
                "firing when GPC was asserted"
            )
            _gpc_honored_icon = _SVG_CHECK
        elif _gpc_respected is False:
            _gpc_verdict_label = "Ignored"
            _gpc_verdict_color = "#ef4444"
            _vcount = audit_result.gpc_vendors_after_signal
            _gpc_honored_text = (
                f"<strong style='color:#ef4444'>NO</strong> — {_vcount} vendor "
                f"pixel{'s' if _vcount != 1 else ''} fired tracking after GPC was asserted"
            )
            _gpc_honored_icon = _SVG_CROSS
        else:
            _gpc_verdict_label = "Inconclusive"
            _gpc_verdict_color = "#f59e0b"
            _gpc_honored_text = "Inconclusive"
            _gpc_honored_icon = _SVG_WARN

        _gpc_rows = '<div style="margin-top:14px;">'
        _gpc_rows += _findings_row(
            "Sec-GPC: 1 header sent on all requests",
            "<strong style='color:#22c55e'>YES</strong>"
            if audit_result.gpc_header_sent
            else "<strong style='color:#ef4444'>NO</strong>",
            _SVG_CHECK if audit_result.gpc_header_sent else _SVG_CROSS,
        )
        _gpc_rows += _findings_row(
            "navigator.globalPrivacyControl = true",
            "<strong style='color:#22c55e'>YES</strong>"
            if audit_result.gpc_navigator_api_set
            else "<strong style='color:#ef4444'>NO</strong>",
            _SVG_CHECK if audit_result.gpc_navigator_api_set else _SVG_CROSS,
        )
        _gpc_rows += _findings_row("Site honored GPC signal", _gpc_honored_text, _gpc_honored_icon)
        _gpc_rows += _findings_row(
            "Baseline pixel firings (post opt-out)",
            f"<code>{audit_result.gpc_pixel_count_baseline}</code>",
            _SVG_DASH,
        )
        _gpc_rows += _findings_row(
            "Pixel firings under GPC",
            f"<code style='color:{'#22c55e' if audit_result.gpc_pixel_count_with_gpc == 0 else '#ef4444'}'>"
            f"{audit_result.gpc_pixel_count_with_gpc}</code>",
            _SVG_CHECK if audit_result.gpc_pixel_count_with_gpc == 0 else _SVG_CROSS,
        )
        _gpc_rows += "</div>"

        _gpc_tag_html = (
            f"<span style=\"font-family:'Inter';font-weight:600;font-size:0.45em;"
            f"letter-spacing:0.14em;text-transform:uppercase;padding:4px 12px;"
            f"border-radius:4px;background:{_gpc_verdict_color}22;color:{_gpc_verdict_color};"
            f'border:1px solid {_gpc_verdict_color}44;vertical-align:middle;margin-left:14px;">'
            f"{_gpc_verdict_label}</span>"
        )

        _gpc_footer = (
            '<div style="margin-top:10px;background:#faf8f2;border-radius:6px;padding:10px 14px;'
            f'border-left:3px solid {_gpc_verdict_color};">'
            '<div style="font-size:0.62em;color:#6b7794;line-height:1.5;">'
            "Under CCPA/CPRA, GPC is a legally binding opt-out signal. "
            "California's CPPA has stated GPC non-compliance is enforceable without prior notice."
            "</div></div>"
        )

        _gpc_slide_md = (
            "---\n\n"
            "<!-- _class: compact -->\n\n"
            "### GPC COMPLIANCE TEST\n\n"
            f"# GPC Compliance {_gpc_tag_html}\n\n"
            '<p style="font-size:0.72em;color:#6b7794;margin:0 0 10px;line-height:1.5;">'
            "Sec-GPC: 1 header + navigator.globalPrivacyControl asserted on every request.</p>"
            f"{_gpc_rows}"
            f"{_gpc_footer}\n"
        )

    # Immediate actions (two-panel)
    _imm = []
    for f in violations[:3]:
        _imm.append(
            f"Disable <strong style='color:#14182b'>{f.vendor.name}</strong> tag in GTM until consent logic is verified"
        )
    if audit_result.ssgtm_detected:
        _imm.append("Audit SSGTM container for consent signal passthrough enforcement")
    _30d = []
    if violations:
        _30d += [
            "Audit CMP integration against Consent Mode V2 requirements",
            "Verify GPC signal is mapped to CMP opt-out state",
            "Obtain written data processing agreements with all third-party vendors",
        ]
    if _gcs_full_denial:
        _30d.append("Document legal basis for cookieless pings under Advanced Consent Mode")
    if _gcs_partial:
        _30d.append(
            f"Extend {audit_result.detected_cmp or 'CMP'} opt-out to deny analytics_storage in addition to ad_storage — "
            f"CCPA 'Do Not Sell' covers analytics profiling, not just ad delivery (GCS={gcs_state} must become G100)"
        )
    if _gcs_cmp_broken:
        _30d.append(
            f"Fix {audit_result.detected_cmp or 'CMP'} → Consent Mode integration: opt-out must propagate denial signals (G100) to all Google tags"
        )
    if clean:
        _30d.append("Schedule quarterly consent audits to catch configuration drift")

    def _action_item(text: str) -> str:
        return (
            f'<div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;'
            f'border-bottom:1px solid #e7e3d8;font-size:0.73em;">'
            f'<div style="flex:0 0 20px;margin-top:2px;">'
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3d6abb" stroke-width="2">'
            f'<polyline points="9 18 15 12 9 6"/></svg></div>'
            f'<div style="color:#9ca3af;font-weight:200;line-height:1.5;">{text}</div></div>'
        )

    _actions_imm_html = (
        "".join(_action_item(a) for a in _imm)
        if _imm
        else _action_item("No immediate actions required — site is compliant")
    )
    _actions_30d_html = "".join(_action_item(a) for a in _30d) if _30d else ""

    # 30-day panel (needs _actions_30d_html to be built first)
    _actions_30d_panel = (
        (
            '<div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:3px solid #3d6abb;">'
            "<div style=\"font-family:'Inter';font-weight:600;font-size:0.62em;color:#3d6abb;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;\">Within 30 Days</div>"
            + _actions_30d_html
            + "</div>"
        )
        if _actions_30d_html
        else ""
    )

    # ── Now build the old-style preprocessing vars still needed ─────────────
    # Status dot SVGs — only used inside HTML <table> blocks where Marp renders inline SVG.
    # Do NOT embed in markdown heading text or pipe-table cells (Marp escapes those).
    def _dot(color: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 11 11">'
            f'<circle cx="5.5" cy="5.5" r="5" fill="{color}"/></svg>'
        )

    # Site image for title slide — OG image data URI or globe SVG fallback
    _GLOBE_SVG = (
        "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        "stroke='%233d6abb' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'>"
        "<circle cx='12' cy='12' r='10'/>"
        "<line x1='2' y1='12' x2='22' y2='12'/>"
        "<path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/>"
        "</svg>"
    )
    _img_src = site_image_url or _GLOBE_SVG
    _has_real_logo = bool(site_image_url)
    # Site logo: top-right corner — white card for real logos, subtle dark for globe fallback
    _logo_bg = "rgba(255,255,255,0.92)" if _has_real_logo else "rgba(255,255,255,0.06)"
    _logo_pad = "10px" if _has_real_logo else "8px"
    _logo_size = "58px" if _has_real_logo else "44px"
    _site_img_html = (
        f'<div style="position:absolute;top:44px;right:60px;'
        f'background:{_logo_bg};border-radius:10px;padding:{_logo_pad};line-height:0;">'
        f'<img src="{_img_src}" style="height:{_logo_size};width:{_logo_size};border-radius:8px;'
        f'object-fit:contain;display:block;" /></div>'
    )

    # KJB brand bar: absolutely positioned at the bottom of the title slide
    _audit_id_full = audit_result.audit_id
    _meta_date = audit_result.timestamp.strftime("%B %d, %Y")
    _meta_method = (
        "Consent Enforcement"
        if audit_result.methodology
        in (MethodologyFlag.S3, MethodologyFlag.S3_CONSENT_WIRING_BROKEN)
        else "Baseline Scan"
    )
    _label_style = "color:#4b5563;font-size:0.42em;font-family:'Inter';font-weight:600;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:4px;"
    _value_style = "font-family:'Inter';font-weight:500;font-size:0.6em;color:#9ca3af;"
    _audit_id_style = (
        "font-family:'Inter';font-weight:500;font-size:0.48em;color:#9ca3af;letter-spacing:0.02em;"
    )
    # Brand selector — "rsc" uses KJB logo + name; "kjb" uses just Kenneth Buchanan (unbranded)
    if brand == "kjb":
        _brand_primary = "Kenneth Buchanan"
        _brand_logo_html = ""
        _closing_kicker = "CONSENT COMPLIANCE INTELLIGENCE"
    else:
        _brand_primary = "KJB"
        _brand_logo_html = (
            f'<img src="data:image/png;base64,{_RSC_ICON_B64}" '
            f'style="height:44px;width:44px;border-radius:8px;flex-shrink:0;" />'
            if _RSC_ICON_B64
            else ""
        )
        _closing_kicker = "ROSE SKY CONSULTING INC."
    _rsc_brand_html = (
        '<div style="position:absolute;bottom:50px;left:72px;right:72px;">'
        '<div style="border-top:1px solid #e7e3d8;padding-top:18px;'
        'display:flex;justify-content:space-between;align-items:center;">'
        # Left: brand logo + name (KJB) or plain name
        f'<div style="display:flex;align-items:center;gap:14px;">'
        f"{_brand_logo_html}"
        f"<div><div style=\"font-family:'Inter';font-weight:700;font-size:0.65em;color:#14182b;line-height:1.2;\">{_brand_primary}</div>"
        f"<div style=\"font-family:'Inter';font-weight:400;font-size:0.46em;color:#4b5563;margin-top:3px;\">Consent Compliance Intelligence</div></div>"
        "</div>"
        # Right: metadata columns — each left-aligned so label sits directly above value
        '<div style="display:flex;gap:36px;align-items:flex-start;">'
        f'<div><div style="{_label_style}">Date</div><div style="{_value_style}">{_meta_date}</div></div>'
        f'<div><div style="{_label_style}">Methodology</div><div style="{_value_style}">{_meta_method}</div></div>'
        f'<div><div style="{_label_style}">Audit ID</div><div style="{_audit_id_style}">{_audit_id_full}</div></div>'
        "</div>"
        "</div></div>"
    )

    # Pre-build the cookie-evidence section outside the f-string. Inlining a
    # backslash-escaped HTML attribute inside an f-string expression breaks
    # mypy on Python 3.12 even though the runtime accepts it (PEP 701).
    _nl = chr(10)
    if violations:
        _cookie_section_md = (
            "### COOKIE EVIDENCE" + _nl + _nl
            + "# Confirmed Violations" + _nl + _nl
            + _vendor_cards_html + _nl + _nl
            + '<div style="margin-top:16px;background:#fbe8e2;border-radius:10px;'
              'padding:14px 18px;border-left:4px solid #ef4444;font-size:0.72em;'
              'color:#9ca3af;line-height:1.7;">'
              "<strong style=\"color:#ef4444;\">CCPA exposure:</strong> "
              "these vendors received behavioral data after consent was denied. "
              "Each firing = potential $7,500 violation."
              "</div>"
        )
    else:
        _cookie_section_md = (
            "### COOKIE ANALYSIS" + _nl + _nl
            + "# No Cookie Violations" + _nl + _nl
            + "<p>No tracking cookies were observed firing after consent was denied.</p>"
        )

    # Build findings summary as a real HTML table so SVG dots render correctly
    slides = f"""---
marp: true
theme: default
paginate: true
footer: '{_brand_primary} · Consent Compliance Intelligence'
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap');

  :root {{
    /* LIGHT theme — warm cream, Anthropic-style, KJB accents */
    --bg:    #f6f4ee;          /* warm cream */
    --s:     #ffffff;          /* surface */
    --s2:    #faf8f2;           /* alt surface */
    --b:     #e7e3d8;          /* border */
    --b2:    #d8d2c2;          /* strong border */
    --t:     #14182b;          /* headline near-black */
    --body:  #1f2944;          /* body near-navy */
    --m:     #6b7794;          /* muted */
    --a:     #3d6abb;          /* KJB blue accent */
    --navy:  #2b3954;          /* KJB navy — section markers */
    --g:     #2f7a4f;          /* green */
    --gs:    #e4f1e6;          /* green-soft */
    --r:     #b34d4d;          /* red */
    --rs:    #fbe8e2;          /* red-soft */
    --y:     #a06913;          /* amber */
    --ys:    #f5ebd2;          /* amber-soft */
  }}
  section {{
    background: var(--bg); color: var(--body);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-weight: 400;
    padding: 72px 96px 88px; line-height: 1.55;
    letter-spacing: -0.003em;
    box-sizing: border-box;
  }}
  section > * {{ max-width: 100%; }}
  footer {{
    font-size: 0.52em; color: var(--m);
    padding: 14px 96px 18px;
    background: var(--bg); position: absolute; bottom: 0; left: 0; right: 0;
    border-top: 1px solid var(--b);
    letter-spacing: 0.08em;
  }}
  h1 {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-weight: 500;
    font-size: 2.6em;
    color: var(--t);
    letter-spacing: -0.022em;
    line-height: 1.12;
    margin: 0 0 14px;
  }}
  h2 {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-weight: 400;
    font-size: 1.15em;
    color: var(--m);
    margin: 0 0 26px;
    letter-spacing: 0;
  }}
  h3 {{
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.6em;
    color: var(--a);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin: 0 0 10px;
  }}
  strong {{ color: var(--t); font-weight: 600; }}
  p {{ color: var(--body); font-size: 0.84em; line-height: 1.65; margin: 0 0 10px; }}
  li {{ color: var(--body); font-size: 0.84em; line-height: 1.65; margin-bottom: 6px; }}
  blockquote {{
    margin: 22px 0 28px;
    padding-left: 22px;
    border-left: 2px solid var(--a);
    font-family: 'Source Serif 4', Georgia, serif;
    font-style: italic;
    font-weight: 400;
    font-size: 0.95em;
    color: var(--body);
  }}
  a {{ color: var(--a); text-decoration: none; border-bottom: 1px solid var(--a); }}
  code {{
    background: var(--s2); color: var(--t);
    padding: 1px 6px; border-radius: 3px; border: 1px solid var(--b);
    font-size: 0.82em; font-family: 'SF Mono', Menlo, monospace;
  }}
  section.lead {{ display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
  section.compact {{ padding: 56px 96px 56px; }}
  section.compact h1 {{ font-size: 2.1em; margin-bottom: 8px; }}
  section.compact h2 {{ font-size: 1em; margin-bottom: 18px; }}
  section.compact p {{ font-size: 0.78em; }}
  section.cover {{ padding: 110px 96px; background: var(--bg); }}
  section.cover h1 {{
    font-size: 3.2em; border-left: 3px solid var(--a);
    padding-left: 28px; margin-bottom: 16px; color: var(--t);
  }}
  section.cover h2 {{
    font-size: 1.05em; padding-left: 31px;
    color: var(--m); margin: 0 0 48px;
  }}
  section.cover .brand-mark {{
    position: absolute; top: 56px; right: 96px;
    width: 64px; height: 64px; display: flex;
    align-items: center; justify-content: center;
    background: var(--s); border: 1px solid var(--b);
    border-radius: 8px; padding: 8px;
    box-shadow: 0 1px 2px rgba(20,24,43,0.04);
  }}
  section.cover .brand-mark img {{
    max-width: 100%; max-height: 100%; object-fit: contain;
    display: block;
  }}
  section::after {{
    font-family: 'Inter', sans-serif; font-size: 0.54em;
    color: var(--m); right: 96px; bottom: 18px; letter-spacing: 0.08em;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.78em; margin: 14px 0 18px; }}
  th {{
    text-align: left; padding: 12px 18px 12px 0;
    color: var(--m); font-weight: 500;
    font-size: 0.74em; text-transform: uppercase; letter-spacing: 0.12em;
    border-bottom: 1px solid var(--b);
  }}
  td {{
    padding: 12px 18px 12px 0; color: var(--body);
    border-bottom: 1px solid var(--b);
  }}
  tr:last-child td {{ border-bottom: none; }}
  .tag {{
    font-family: 'Inter', sans-serif; font-weight: 600;
    font-size: 0.52em; letter-spacing: 0.12em;
    text-transform: uppercase; padding: 3px 9px;
    border-radius: 3px; display: inline-block;
  }}
  details {{
    background: var(--s); border: 1px solid var(--b);
    border-radius: 5px; padding: 14px 18px; margin-top: 8px;
  }}
  details summary {{ color: var(--a); font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.78em; cursor: pointer; }}
  details p {{ color: var(--body); font-size: 0.76em; margin-top: 8px; line-height: 1.6; }}
---

<style>section:first-of-type > footer {{ display: none !important; }}</style>

### FORENSIC PRIVACY AUDIT · {jurisdiction} · CONFIDENTIAL

{_site_img_html}

# {url_display}

## Consent Compliance Report

{_rsc_brand_html}

---

### AUDIT VERDICT

# {"Violations Confirmed" if (violations or pixel_violations) else "No Violations Detected"}

<p style="font-size:0.72em;color:#9ca3af;max-width:680px;line-height:1.6;margin-bottom:0;">{_slide_summary(executive_summary)}</p>

{_verdict_cards}

---

### SIGNAL ANALYSIS

# Findings at a Glance

{_fr}

---

{_cookie_section_md}

{"---" + chr(10) + chr(10) + _pixel_marp_section if _pixel_marp_section else ""}

{"---" + chr(10) + chr(10) + "<!-- _class: compact -->" + chr(10) + chr(10) + "### RISK QUANTIFICATION" + chr(10) + chr(10) + "# Financial Exposure Estimate" + chr(10) + chr(10) + _exposure_html if (violations or pixel_violations) else ""}

{_gpc_slide_md}

{_cmp_runtime_slide_md}

---

### {"GDPR · EPRIVACY DIRECTIVE" if jurisdiction == "EU" else "CCPA · CPRA · CIPA · FTC ACT"}

# Applicable Legal Framework

<div style="margin-top:8px;">
{_law_items_html}
</div>

---

### REMEDIATION ROADMAP

# {"Immediate Actions Required" if violations else "Maintaining Compliance"}

<div style="display:flex;gap:12px;margin-top:10px;">
  <div style="{_action_panel_style}">
    <div style="{_action_hdr_style}">{_action_label}</div>
    {_actions_imm_html}
  </div>
  {_actions_30d_panel}
</div>

---

### HOW WE AUDIT

# Forensic Methodology

<p style="font-size:0.75em;color:#6b7280;margin-bottom:12px;">{methodology_label} — Independent forensic scan. No vendor access or cooperation required. Mirrors the approach used by the <strong style="color:#22c55e;">California Privacy Protection Agency</strong> in automated GPC compliance sweeps.</p>

<div style="margin-top:4px;">
{"".join(_action_item(a) for a in ["Fresh browser context — zero prior cookies, consent denial pre-injected before page load", "Page reloaded post-denial to capture true opted-out network state", "All network traffic captured and fingerprinted against 3,200+ vendor signatures", "Pixel endpoint detection — plaintiff law firm methodology (CIPA §631)", "Regulatory findings cross-referenced against live enforcement database"])}
</div>

---

### PREPARED BY

# Kenneth Buchanan

<p style="font-size:0.72em;color:#6b7280;margin:-8px 0 0 0;">Independent forensic audit · <a href="https://kennethjbuchanan.com" style="color:#3d6abb;text-decoration:none;">kennethjbuchanan.com</a></p>

<div style="display:flex;gap:10px;margin-top:28px;">
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:2px solid var(--a);">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:var(--a);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px;">Forensic Auditing</div>
    <div style="font-size:0.72em;color:#6b7280;line-height:1.8;">Post-denial traffic analysis<br>GPC signal testing<br>SSGTM detection</div>
  </div>
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:2px solid var(--a);">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:var(--a);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px;">Regulatory Intelligence</div>
    <div style="font-size:0.72em;color:#6b7280;line-height:1.8;">Live US &amp; EU enforcement data<br>Fine exposure modeling<br>Case precedent library</div>
  </div>
  <div style="flex:1;background:var(--s);border-radius:10px;padding:20px;border-top:2px solid var(--a);">
    <div style="font-family:'Inter';font-weight:600;font-size:0.62em;color:var(--a);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px;">Remediation Advisory</div>
    <div style="font-size:0.72em;color:#6b7280;line-height:1.8;">CMP configuration<br>Consent Mode V2<br>GTM consent architecture</div>
  </div>
</div>

<div style="margin-top:20px;font-size:0.6em;color:#4b5563;line-height:1.6;">
Audit {audit_result.audit_id} · {audit_result.timestamp.strftime('%Y-%m-%d')} · For compliance assessment purposes only. Consult legal counsel for enforcement risk analysis.
</div>
"""

    return slides.strip()
