"""Evaluation runner.

Iterates every YAML in evals/cases/, runs the audit, compares to the
expected block, prints a roll-up. Designed to run in CI.

Usage:
    python evals/run_evals.py
    python evals/run_evals.py --add-baseline evals/cases/001-foo.yaml
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


async def _run_one(case: dict[str, Any]) -> dict[str, Any]:
    from consent_engine.tools.tool_02_violation_classifier import classify
    from consent_engine.tools.tool_03_browser_scanner import scan_page

    t0 = time.perf_counter()
    scan = await scan_page(url=case["url"])
    audit = classify(scan)
    elapsed = time.perf_counter() - t0

    actual = {
        "violations_count": len(audit.violations),
        "has_definitive_findings": any(
            v.confidence == "definitive" for v in audit.violations
        ),
        "cmp_detected": audit.cmp.name if audit.cmp else None,
        "consent_mode_state": audit.consent_mode_state,
    }
    expected = case.get("expected", {})
    failures = {k: (actual[k], expected[k]) for k in expected if k in actual and actual[k] != expected[k]}
    return {
        "name": case["name"],
        "url": case["url"],
        "elapsed_s": round(elapsed, 2),
        "actual": actual,
        "expected": expected,
        "failures": failures,
        "passed": not failures,
    }


def _load_cases() -> list[dict[str, Any]]:
    return [yaml.safe_load(p.read_text()) for p in sorted(CASES_DIR.glob("*.yaml"))]


def _print_rollup(results: list[dict[str, Any]]) -> int:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    elapsed = [r["elapsed_s"] for r in results]
    p50 = statistics.median(elapsed) if elapsed else 0
    p95 = sorted(elapsed)[int(0.95 * len(elapsed))] if len(elapsed) > 1 else (elapsed[0] if elapsed else 0)
    print("=" * 60)
    print(f"PASS {passed}/{total}  ·  p50 {p50:.1f}s  ·  p95 {p95:.1f}s")
    for r in results:
        mark = "✓" if r["passed"] else "✗"
        print(f"  {mark} {r['name']}  ({r['elapsed_s']:.1f}s)")
        for k, (got, want) in (r["failures"] or {}).items():
            print(f"      {k}: got {got!r}, expected {want!r}")
    print("=" * 60)
    return 0 if passed == total else 1


async def _add_baseline(case_path: Path) -> int:
    case = yaml.safe_load(case_path.read_text())
    result = await _run_one(case)
    case["expected"] = result["actual"]
    case_path.write_text(yaml.safe_dump(case, sort_keys=False))
    print(f"baseline updated: {case_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add-baseline", help="Re-baseline a single case YAML.")
    args = parser.parse_args(argv)

    if args.add_baseline:
        return asyncio.run(_add_baseline(Path(args.add_baseline)))

    if not CASES_DIR.exists() or not list(CASES_DIR.glob("*.yaml")):
        print(f"No eval cases in {CASES_DIR}. Add some — see evals/README.md.")
        return 0

    cases = _load_cases()
    results = asyncio.run(asyncio.gather(*(_run_one(c) for c in cases)))
    return _print_rollup(list(results))


if __name__ == "__main__":
    sys.exit(main())
