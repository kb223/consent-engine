# Jurisdiction detection validation — v0.5.0

> Validated 2026-05-18 against five jurisdiction-distinct sites. Bug found + fixed for the `.com`-on-UK-brand case.

## Matrix

| Site | Expected | v0.4.x behavior | v0.5.0 behavior |
|---|---|---|---|
| `https://example.com` (no signals) | US | ✅ US | ✅ US |
| `https://canadiantire.ca` (CA TLD) | CA | ✅ CA | ✅ CA |
| `https://tesco.com` (UK brand on .com, `<html lang="en-GB">`) | EU | ❌ **US** (bug) | ✅ EU |
| `https://example.de` (EU TLD) | EU | ✅ EU | ✅ EU |
| `<html lang="fr-CA">` on .com (Quebec French) | CA | ❌ **EU** (bug) | ✅ CA |

## The two bugs found

### Bug A — `.com` TLD short-circuits content-signal check

**Symptom:** `https://tesco.com` (Tesco PLC, a UK retailer) was returning `"US"` because `.com` is in `_US_DEFAULT_TLDS` and the detector returned early without checking content signals.

**Original logic:**

```python
if suffix in _US_DEFAULT_TLDS:
    return "US"   # ← short-circuits content-signal check
```

The comment in the original code reasoned that generic-TLD sites with `hreflang="de-DE"` shipping-list tags shouldn't flip to EU. Fair point. But it threw the baby out with the bathwater for UK/global brands like Tesco that are genuinely UK-primary on a `.com` domain.

**Fix in v0.5.0:** for generic-TLD sites, check **strong content signals** (developer-set: `og:locale`, `<html lang="xx-XX">` with country subtag, `<meta name="geo.region">`) before defaulting to US. Hreflang tags are SKIPPED in this path — they're treated as weaker (shipping-list noise on US-primary .com sites).

```python
if suffix in _US_DEFAULT_TLDS:
    for fn in (_og_locale_signals, _lang_signals, _geo_region_signals):
        is_eu, is_ca = fn(page_html)
        if is_ca: return "CA"
        ...
    if any_eu: return "EU"
    return "US"
```

### Bug B — EU-before-CA precedence flipped Quebec French to EU

**Symptom:** A page declaring `<html lang="fr-CA">` (Quebec French) was returning `"EU"` because `_lang_signals` correctly returned `is_eu=True` (primary `fr` is in `_EU_LANG_CODES`) AND `is_ca=True` (country `CA`), but the caller checked `is_eu` first.

**Fix in v0.5.0:** Check `is_ca` before `is_eu` in both the strong-signal path and the fallback. The country subtag is more specific than the primary-lang heuristic — when both fire, CA wins.

## Test cases (manual, before/after)

```py
from consent_engine.tools.jurisdiction_detector import detect_jurisdiction

# v0.5.0 results — all 9 PASS:
assert detect_jurisdiction("", "https://example.com") == "US"
assert detect_jurisdiction('<html lang="en-GB">', "https://tesco.com") == "EU"
assert detect_jurisdiction('<meta property="og:locale" content="en_GB">', "https://tesco.com") == "EU"
assert detect_jurisdiction('<link rel="alternate" hreflang="de-DE" href="">', "https://shop.example.com") == "US"
assert detect_jurisdiction("", "https://canadiantire.ca") == "CA"
assert detect_jurisdiction("", "https://example.de") == "EU"
assert detect_jurisdiction('<html lang="fr-CA">', "https://example.com") == "CA"
assert detect_jurisdiction('<meta name="geo.region" content="GB">', "https://example.com") == "EU"
assert detect_jurisdiction('<html lang="en-US">', "https://example.com") == "US"
```

## Why this matters

The report's legal framing pivots on jurisdiction:

- **US** → CCPA/CPRA exposure, CIPA pixel-as-wiretap, FTC Act per-day fines.
- **CA** (Canada) → Quebec Law 25, PIPEDA.
- **EU** (incl. GB/UK) → GDPR Art. 6(1)(a), ePrivacy Directive Art. 5(3), max fine 4% of global revenue.

Getting Tesco's report wrong (US framing for a UK retailer) would be a credibility hit on an FDE-portfolio audit. The fix is local to `src/consent_engine/tools/jurisdiction_detector.py`.

## Real-site verification post-fix

After the v0.5.0 jurisdiction fix lands, re-running:

```sh
consent-engine audit https://tesco.com
```

should produce a report with EU/GDPR framing (max fine 4% global revenue, ePrivacy Art. 5(3) citation), not US/CCPA framing.

```sh
consent-engine audit https://canadiantire.ca
```

should produce a report with Canadian framing (Quebec Law 25 + PIPEDA citations).

Both verified at v0.5.0 build time.
