"""Scorecard for investigator runs. Offline: it reads saved results, never the API.

    uv run python evals/score.py out/investigator
    uv run python evals/score.py out/investigator/claude-opus-5-5 --labels evals/fixtures/labels.csv

Three kinds of result, kept apart on purpose:

- Evidence checks are deterministic and need no labels. A run fails if it cites
  a request that doesn't exist, cites one no tool returned, gives a strong
  verdict with no citation, or doesn't cover the scanner's findings.
- Label metrics compare verdicts with hand labels. They are skipped, and say
  so, until the label sheet has verdicts in it.
- Agreement with the scanner is reported for context only. The scanner is not
  ground truth.

A run that didn't complete is counted as incomplete. It is never scored as if
the agent had answered.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fixture_tools import FIXTURES_DIR, Fixture, load_fixture, run_tool

STRONG_VERDICTS = {"confirmed_violation", "likely_violation"}
UNSETTLED = "requires_further_investigation"

# Checks that fail a run. One fabricated citation is enough.
HARD_CHECKS = (
    "missing_findings",
    "extra_findings",
    "duplicate_findings",
    "fabricated_request_ids",
    "unseen_request_ids",
    "uncited_strong_verdicts",
    "wrong_audit_status",
)
# Checks that are reported but don't fail a run on their own.
SOFT_CHECKS = (
    "non_citable_request_ids",
    "unknown_cookies",
    "unsettled_not_escalated",
    "escalated_without_reason",
    "blocked_wording",
)

# Wording the report guardrails block. A heuristic, so it is a soft check.
BLOCKED_WORDING = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\billegal(ly)?\b",
        r"\bunlawful(ly)?\b",
        r"\bliable\b",
        r"\bwill be fined\b",
        r"\b(broke|breaks|breached|breaches|violated|violates) (the |a )?(law|statute|gdpr|ccpa|cpra)\b",
        r"\bregulatory violation proven\b",
        r"\bdark pattern confirmed\b",
        r"\b(no|without|absence of|free of) server-side (tracking|tagging)\b",
        r"\bserver-side (tracking|tagging) (is|was) (absent|not present|not used|not in use)\b",
        r"\b(does not|doesn't) use server-side\b",
    )
]

VERDICT_ALIASES = {
    "confirmed": "confirmed_violation",
    "likely": "likely_violation",
    "rfi": UNSETTLED,
    "investigate": UNSETTLED,
    "unclear": UNSETTLED,
    "none": "no_evidence_of_violation",
    "no_evidence": "no_evidence_of_violation",
    "acm": "acm_cookieless_ping",
}
YES = {"yes", "y", "true", "1"}
NO = {"no", "n", "false", "0"}


@dataclass
class RunScore:
    fixture_id: str
    model: str
    run: int
    outcome: str
    path: str
    cost_usd: float | None = None
    served_models: list[str] = field(default_factory=list)
    checks: Counter[str] = field(default_factory=Counter)
    details: list[str] = field(default_factory=list)
    # finding_id -> (verdict, escalate), only for completed runs
    verdicts: dict[str, tuple[str, bool]] = field(default_factory=dict)

    @property
    def completed(self) -> bool:
        return self.outcome == "completed"

    @property
    def passed(self) -> bool:
        return self.completed and not any(self.checks[name] for name in HARD_CHECKS)


def _returned_request_ids(fixture: Fixture, tool_calls: list[dict[str, Any]]) -> set[str]:
    """Request IDs the tools handed to the agent in this run.

    The tools are deterministic, so replaying the logged calls gives the same
    results the agent saw.
    """
    seen: set[str] = set()
    for call in tool_calls:
        result = run_tool(fixture, str(call.get("name")), call.get("input"))
        for match in result.get("matches", []):
            seen.add(match["request_id"])
        if "request" in result:
            seen.add(result["request"]["request_id"])
        if "finding" in result:
            seen.update(result["finding"]["linked_request_ids"])
    return seen


def _expected_audit_status(fixture: Fixture) -> str:
    if fixture.manifest.get("scan_outcome") == "failed":
        return "scan_failed"
    return "investigated"


def _text_fields(output: dict[str, Any]) -> list[str]:
    texts = [str(output.get("notes", ""))]
    for finding in output.get("findings", []):
        texts += [
            str(finding.get(key, "")) for key in ("claim", "root_cause", "fix", "escalation_reason")
        ]
    return texts


def score_run(result: dict[str, Any], fixture: Fixture, path: str = "") -> RunScore:
    """Run every evidence check on one saved result."""
    score = RunScore(
        fixture_id=str(result.get("fixture_id")),
        model=str(result.get("model")),
        run=int(result.get("run") or 1),
        outcome=str(result.get("outcome")),
        path=path,
        cost_usd=result.get("cost_usd"),
        served_models=list(result.get("served_models") or []),
    )
    output = result.get("output")
    if not score.completed or not isinstance(output, dict):
        return score

    def flag(check: str, detail: str, count: int = 1) -> None:
        score.checks[check] += count
        score.details.append(f"{check}: {detail}")

    scanner_ids = [str(f.get("finding_id")) for f in fixture.findings]
    findings = [f for f in output.get("findings", []) if isinstance(f, dict)]
    agent_ids = [str(f.get("finding_id")) for f in findings]

    expected_status = _expected_audit_status(fixture)
    if output.get("audit_status") != expected_status:
        flag("wrong_audit_status", f"{output.get('audit_status')} (expected {expected_status})")
    if expected_status != "investigated":
        if findings:
            flag("extra_findings", "findings returned for a scan that can't be assessed")
        return score

    for missing in sorted(set(scanner_ids) - set(agent_ids)):
        flag("missing_findings", missing)
    for extra in sorted(set(agent_ids) - set(scanner_ids)):
        flag("extra_findings", extra)
    for finding_id, count in Counter(agent_ids).items():
        if count > 1:
            flag("duplicate_findings", finding_id, count - 1)

    requests = {str(r.get("request_id")): r for r in fixture.requests}
    returned = _returned_request_ids(fixture, list(result.get("tool_calls") or []))
    scanner_cookies = {
        str(f.get("finding_id")): set(f.get("cookies_observed") or []) for f in fixture.findings
    }

    for finding in findings:
        finding_id = str(finding.get("finding_id"))
        verdict = str(finding.get("verdict"))
        escalate = bool(finding.get("escalate"))
        cited_requests = [str(i) for i in finding.get("cited_request_ids") or []]
        cited_cookies = [str(c) for c in finding.get("cited_cookies") or []]
        score.verdicts[finding_id] = (verdict, escalate)

        for request_id in cited_requests:
            if request_id not in requests:
                flag("fabricated_request_ids", f"{finding_id} cites {request_id}")
            elif request_id not in returned:
                flag("unseen_request_ids", f"{finding_id} cites {request_id}")
            elif not requests[request_id].get("citable"):
                flag("non_citable_request_ids", f"{finding_id} cites {request_id}")
        for cookie in cited_cookies:
            if cookie not in scanner_cookies.get(finding_id, set()):
                flag("unknown_cookies", f"{finding_id} cites {cookie}")
        if verdict in STRONG_VERDICTS and not cited_requests and not cited_cookies:
            flag("uncited_strong_verdicts", finding_id)
        if verdict == UNSETTLED and not escalate:
            flag("unsettled_not_escalated", finding_id)
        if escalate and not str(finding.get("escalation_reason", "")).strip():
            flag("escalated_without_reason", finding_id)

    for text in _text_fields(output):
        for pattern in BLOCKED_WORDING:
            found = pattern.search(text)
            if found:
                flag("blocked_wording", repr(found.group(0)))
    return score


def load_scores(runs_dir: Path, fixtures_dir: Path = FIXTURES_DIR) -> list[RunScore]:
    scores = []
    for path in sorted(runs_dir.rglob("*.json")):
        try:
            result = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if not isinstance(result, dict) or "fixture_id" not in result or "outcome" not in result:
            continue
        try:
            fixture = load_fixture(str(result["fixture_id"]), fixtures_dir)
        except FileNotFoundError:
            print(f"Skipping {path}: fixture {result['fixture_id']} not found.", file=sys.stderr)
            continue
        scores.append(score_run(result, fixture, str(path)))
    return scores


def normalise_verdict(raw: str) -> str | None:
    value = raw.strip().lower().replace(" ", "_").replace("-", "_")
    if not value:
        return None
    return VERDICT_ALIASES.get(value, value)


def load_labels(sheet: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Read hand labels. Rows with no verdict are skipped."""
    labels: dict[tuple[str, str], dict[str, Any]] = {}
    if not sheet.exists():
        return labels
    with sheet.open(newline="") as handle:
        for row in csv.DictReader(handle):
            verdict = normalise_verdict(row.get("kenneth_verdict") or "")
            if verdict is None:
                continue
            raw_escalate = (row.get("should_escalate") or "").strip().lower()
            escalate = True if raw_escalate in YES else False if raw_escalate in NO else None
            labels[(row["fixture"], row["finding_id"])] = {
                "verdict": verdict,
                "escalate": escalate,
                "scanner_verdict": row.get("status_today") or row.get("engine_status") or "",
            }
    return labels


def label_metrics(
    scores: list[RunScore], labels: dict[tuple[str, str], dict[str, Any]]
) -> dict[str, Any] | None:
    """Compare completed runs with hand labels. None when nothing overlaps."""
    judged = agree = false_positives = not_strong = 0
    escalation_judged = escalation_agree = 0
    for score in scores:
        for finding_id, (verdict, escalate) in score.verdicts.items():
            label = labels.get((score.fixture_id, finding_id))
            if label is None:
                continue
            judged += 1
            agree += verdict == label["verdict"]
            if label["verdict"] not in STRONG_VERDICTS:
                not_strong += 1
                false_positives += verdict in STRONG_VERDICTS
            if label["escalate"] is not None:
                escalation_judged += 1
                escalation_agree += escalate == label["escalate"]
    if not judged:
        return None
    majority = Counter(label["verdict"] for label in labels.values()).most_common(1)[0]
    scanner_agree = sum(label["scanner_verdict"] == label["verdict"] for label in labels.values())
    return {
        "judged": judged,
        "agreement": agree / judged,
        "false_positive_rate": false_positives / not_strong if not_strong else None,
        "escalation_accuracy": (
            escalation_agree / escalation_judged if escalation_judged else None
        ),
        "scanner_agreement": scanner_agree / len(labels),
        "majority_baseline": majority[1] / len(labels),
        "majority_verdict": majority[0],
    }


def verdict_stability(scores: list[RunScore]) -> tuple[int, int] | None:
    """How many findings got the same verdict in every completed run.

    Returns (stable, total) over findings seen in two or more runs, or None
    when no fixture was run more than once.
    """
    by_finding: dict[tuple[str, str], list[str]] = defaultdict(list)
    for score in scores:
        for finding_id, (verdict, _) in score.verdicts.items():
            by_finding[(score.fixture_id, finding_id)].append(verdict)
    repeated = [verdicts for verdicts in by_finding.values() if len(verdicts) > 1]
    if not repeated:
        return None
    return sum(len(set(verdicts)) == 1 for verdicts in repeated), len(repeated)


def scanner_agreement(scores: list[RunScore], fixtures_dir: Path) -> tuple[int, int]:
    agree = total = 0
    cache: dict[str, dict[str, str]] = {}
    for score in scores:
        if score.fixture_id not in cache:
            fixture = load_fixture(score.fixture_id, fixtures_dir)
            cache[score.fixture_id] = {
                str(f.get("finding_id")): str(f.get("status_today") or f.get("engine_status"))
                for f in fixture.findings
            }
        for finding_id, (verdict, _) in score.verdicts.items():
            if finding_id in cache[score.fixture_id]:
                total += 1
                agree += verdict == cache[score.fixture_id][finding_id]
    return agree, total


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def render_scorecard(
    scores: list[RunScore],
    labels: dict[tuple[str, str], dict[str, Any]],
    fixtures_dir: Path = FIXTURES_DIR,
) -> str:
    lines: list[str] = []
    by_model: dict[str, list[RunScore]] = defaultdict(list)
    for score in scores:
        by_model[score.model].append(score)

    for model, runs in sorted(by_model.items()):
        completed = [r for r in runs if r.completed]
        passed = [r for r in runs if r.passed]
        lines.append(f"== {model} ==")
        lines.append(f"Runs: {len(runs)} across {len({r.fixture_id for r in runs})} fixture(s)")
        lines.append(f"Completed: {len(completed)} of {len(runs)}")
        for outcome, count in sorted(Counter(r.outcome for r in runs if not r.completed).items()):
            lines.append(f"  not scored, {outcome}: {count}")
        lines.append(f"Passed every evidence check: {len(passed)} of {len(completed)} completed")

        totals: Counter[str] = Counter()
        for run in completed:
            totals.update(run.checks)
        lines.append("Evidence checks that fail a run:")
        lines += [f"  {name}: {totals[name]}" for name in HARD_CHECKS]
        lines.append("Reported only:")
        lines += [f"  {name}: {totals[name]}" for name in SOFT_CHECKS]

        substituted = sorted({m for r in runs for m in r.served_models if m != model})
        if substituted:
            lines.append(f"WARNING: responses came from {', '.join(substituted)}")

        stability = verdict_stability(completed)
        if stability is None:
            lines.append("Verdict stability: n/a (each fixture ran once)")
        else:
            lines.append(
                f"Verdict stability: {stability[0]} of {stability[1]} findings "
                "got the same verdict in every run"
            )

        costs = [r.cost_usd for r in runs if r.cost_usd is not None]
        if costs:
            lines.append(
                f"Cost: ${sum(costs):.2f} total, ${statistics.mean(costs):.3f} mean per run, "
                f"${max(costs):.3f} max"
            )

        agree, total = scanner_agreement(completed, fixtures_dir)
        if total:
            lines.append(
                f"Same verdict as the scanner: {agree} of {total} "
                "(context only, the scanner is not ground truth)"
            )

        metrics = label_metrics(completed, labels)
        if metrics is None:
            lines.append("Label metrics: skipped, no hand labels match these runs")
        else:
            lines.append(f"Label metrics over {metrics['judged']} judged verdict(s):")
            lines.append(f"  agreement with labels: {_percent(metrics['agreement'])}")
            lines.append(f"  false positive rate: {_percent(metrics['false_positive_rate'])}")
            lines.append(f"  escalation accuracy: {_percent(metrics['escalation_accuracy'])}")
            lines.append(
                f"  baselines: scanner {_percent(metrics['scanner_agreement'])}, "
                f"always '{metrics['majority_verdict']}' {_percent(metrics['majority_baseline'])}"
            )
        lines.append("")

    failing = [r for r in scores if r.completed and not r.passed]
    if failing:
        lines.append("Runs that failed an evidence check:")
        for run in failing:
            lines.append(f"  {run.fixture_id} run {run.run} ({run.model})")
            lines += [f"    {d}" for d in run.details if d.split(":")[0] in HARD_CHECKS]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score saved investigator runs.")
    parser.add_argument("runs_dir", type=Path, help="Folder of saved results.")
    parser.add_argument("--labels", type=Path, default=FIXTURES_DIR / "labels.csv")
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_DIR)
    args = parser.parse_args(argv)

    scores = load_scores(args.runs_dir, args.fixtures)
    if not scores:
        print(f"No saved results under {args.runs_dir}.", file=sys.stderr)
        return 2
    print(render_scorecard(scores, load_labels(args.labels), args.fixtures), end="")
    # Fail when any run failed a hard check or never produced an answer.
    return 0 if all(score.passed for score in scores) else 1


if __name__ == "__main__":
    raise SystemExit(main())
