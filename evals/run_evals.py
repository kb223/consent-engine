"""Evaluation runner.

Iterates every YAML in evals/cases/, runs the audit via the canonical
`consent_engine.audit.run_audit()` pipeline, compares the result to the
expected block, and prints a roll-up.

Usage:
    python evals/run_evals.py                                  # run all cases
    python evals/run_evals.py --add-baseline evals/cases/001-foo.yaml
    python evals/run_evals.py --case evals/cases/001-foo.yaml  # single case

Eval YAML schema (see evals/cases/*.yaml for examples):

    name: "Human-readable case name"
    url: "https://example.com/"
    methodology: "S3"                 # informational only; run_audit always uses S3
    notes: |
      Free-form context. Why this case matters, when to re-baseline.
    expected:
      # Hard equality match
      has_definitive_findings: true|false   # any finding with status=definitive
      cmp_detected: "onetrust"|null
      consent_state: "OPTED_OUT"
      # Bounded checks (use either, not both)
      violations_count: 0                   # exact match
      violations_count_at_least: 1
      violations_count_at_most: 2

Exit codes:
    0  all cases passed
    1  one or more cases failed
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:
    raise SystemExit("evals require pyyaml: pip install pyyaml") from e

CASES_DIR = Path(__file__).resolve().parent / "cases"


# Map AuditResult shape → eval-comparable dict. Adding fields here makes
# them automatically checkable from any case YAML.
def _bundle_to_actuals(bundle: Any) -> dict[str, Any]:
    audit = bundle.audit_result
    scan = bundle.scan_result
    findings = audit.findings or []

    # has_definitive_findings: any finding with a status indicating a confirmed
    # violation. VendorFinding.status is a ViolationStatus StrEnum; the current
    # confirmed value is "confirmed_violation" (was renamed from the old
    # violation_definitive / violation_pre_consent — those no longer exist).
    definitive_statuses = {"confirmed_violation"}
    has_definitive = any(
        str(getattr(f, "status", "")).split(".")[-1].lower() in definitive_statuses
        for f in findings
    )
    confirmed_count = sum(
        1
        for f in findings
        if str(getattr(f, "status", "")).split(".")[-1].lower() in definitive_statuses
    )

    rc = audit.cmp_runtime_config

    return {
        "violations_count": len(findings),
        "confirmed_violations_count": confirmed_count,
        "has_definitive_findings": has_definitive,
        "cmp_detected": (audit.detected_cmp or "").lower() or None,
        "cmp_confidence": (audit.cmp_detection_confidence or "").lower() or None,
        "jurisdiction": (audit.detected_jurisdiction or "").upper() or None,
        "cmp_template": (rc.template_name if rc else None),
        "consent_state": str(getattr(scan, "consent_state", "")).split(".")[-1],
    }


def _check_expectations(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, tuple]:
    """Return {field: (got, want, reason)} for each failed expectation."""
    failures: dict[str, tuple] = {}

    _conf_rank = {"low": 0, "medium": 1, "high": 2}
    for k, want in expected.items():
        if k == "violations_count_at_least":
            got = actual.get("violations_count", 0)
            if got < want:
                failures[k] = (got, f">= {want}", "below floor")
        elif k == "violations_count_at_most":
            got = actual.get("violations_count", 0)
            if got > want:
                failures[k] = (got, f"<= {want}", "above ceiling")
        elif k == "confirmed_violations_count_at_least":
            got = actual.get("confirmed_violations_count", 0)
            if got < want:
                failures[k] = (got, f">= {want}", "below floor")
        elif k == "cmp_confidence_at_least":
            got_conf = actual.get("cmp_confidence")
            got_rank = _conf_rank.get(str(got_conf).lower(), -1)
            want_rank = _conf_rank.get(str(want).lower(), 0)
            if got_rank < want_rank:
                failures[k] = (got_conf, f">= {want}", "confidence below floor")
        elif k in actual:
            got = actual[k]
            if got != want:
                failures[k] = (got, want, "mismatch")
        # Unknown keys silently ignored — lets YAMLs carry notes the runner
        # doesn't enforce yet.
    return failures


async def _run_one(case: dict[str, Any]) -> dict[str, Any]:
    # Late import — keeps the runner's --help fast and avoids pulling
    # Playwright on a no-op invocation.
    from consent_engine.audit import run_audit

    t0 = time.perf_counter()
    try:
        bundle = await run_audit(url=case["url"])
        actual = _bundle_to_actuals(bundle)
        error = None
    except Exception as e:                                  # noqa: BLE001
        actual = {}
        error = f"{type(e).__name__}: {e}"
    elapsed = time.perf_counter() - t0

    failures = _check_expectations(actual, case.get("expected", {})) if not error else {}

    return {
        "name": case["name"],
        "url": case["url"],
        "elapsed_s": round(elapsed, 2),
        "actual": actual,
        "expected": case.get("expected", {}),
        "failures": failures,
        "error": error,
        "passed": (not failures) and (error is None),
    }


def _load_cases(only: Path | None = None) -> list[dict[str, Any]]:
    if only:
        return [yaml.safe_load(only.read_text())]
    return [yaml.safe_load(p.read_text()) for p in sorted(CASES_DIR.glob("*.yaml"))]


def _print_rollup(results: list[dict[str, Any]]) -> int:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    elapsed = [r["elapsed_s"] for r in results]
    p50 = statistics.median(elapsed) if elapsed else 0.0
    p95 = sorted(elapsed)[int(0.95 * len(elapsed))] if len(elapsed) > 1 else (elapsed[0] if elapsed else 0.0)
    print("=" * 70)
    print(f"PASS {passed}/{total}  ·  p50 {p50:.1f}s  ·  p95 {p95:.1f}s")
    for r in results:
        mark = "✓" if r["passed"] else "✗"
        print(f"  {mark}  {r['name']}  ({r['elapsed_s']:.1f}s)")
        if r["error"]:
            print(f"      ERROR: {r['error']}")
        for k, (got, want, reason) in (r["failures"] or {}).items():
            print(f"      {k}: got {got!r}, expected {want!r}  ({reason})")
    print("=" * 70)
    return 0 if passed == total else 1


async def _add_baseline(case_path: Path) -> int:
    case = yaml.safe_load(case_path.read_text())
    result = await _run_one(case)
    if result["error"]:
        print(f"baseline update FAILED: {result['error']}", file=sys.stderr)
        return 1
    case["expected"] = result["actual"]
    case_path.write_text(yaml.safe_dump(case, sort_keys=False))
    print(f"baseline updated: {case_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add-baseline", help="Re-baseline a single case YAML.")
    parser.add_argument("--case", help="Run only this case YAML (path).")
    args = parser.parse_args(argv)

    if args.add_baseline:
        return asyncio.run(_add_baseline(Path(args.add_baseline)))

    if not CASES_DIR.exists() or not list(CASES_DIR.glob("*.yaml")):
        print(f"No eval cases in {CASES_DIR}. Add some — see evals/README.md.")
        return 0

    cases = _load_cases(only=Path(args.case) if args.case else None)

    # Run in parallel so a 4-case sweep takes ~one scan's worth of time.
    # NOTE: asyncio.gather() must be created INSIDE a running event loop —
    # calling asyncio.run(asyncio.gather(...)) builds the gather future before
    # the loop exists, which raises on Python 3.12+ and hard-crashes on 3.14.
    # Wrapping in a coroutine defers gather() construction until the loop runs.
    async def _run_all() -> list[dict[str, object]]:
        return await asyncio.gather(*(_run_one(c) for c in cases))

    results = asyncio.run(_run_all())
    return _print_rollup(list(results))


if __name__ == "__main__":
    sys.exit(main())
