"""Tests for evals/score.py. All data here is synthetic."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

EVALS_DIR = Path(__file__).resolve().parents[1] / "evals"
if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))

sc = importlib.import_module("score")
ft = importlib.import_module("fixture_tools")

REQUESTS = [
    {"request_id": "req_a", "url": "https://t.example/a", "citable": True},
    {"request_id": "req_b", "url": "https://t.example/b", "citable": True},
    {"request_id": "req_old", "url": "https://t.example/old", "citable": False},
]
FINDINGS = [
    {
        "finding_id": "fnd_1",
        "vendor": "Tracker Co",
        "status_today": "confirmed_violation",
        "cookies_observed": ["_trk"],
        "link_status": "request_linked",
        "linked_request_ids": ["req_a"],
    },
    {
        "finding_id": "fnd_2",
        "vendor": "Mystery",
        "status_today": "requires_further_investigation",
        "cookies_observed": ["_m"],
        "link_status": "not_checked",
        "linked_request_ids": [],
    },
]


def _write_fixture(root: Path, fixture_id: str = "fx-01", scan_outcome: str = "complete") -> None:
    folder = root / fixture_id
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(
        json.dumps({"fixture_id": fixture_id, "scan_outcome": scan_outcome, "evidence_saved": True})
    )
    (folder / "audit_result.json").write_text("{}")
    rows = {"requests.jsonl": REQUESTS, "findings.jsonl": FINDINGS}
    for name, items in rows.items():
        (folder / name).write_text("".join(json.dumps(i) + "\n" for i in items))


def _finding(finding_id: str, verdict: str, **overrides: Any) -> dict[str, Any]:
    finding = {
        "finding_id": finding_id,
        "vendor": "v",
        "verdict": verdict,
        "claim": "A request was observed after opt-out.",
        "cited_request_ids": [],
        "cited_cookies": [],
        "root_cause": "undetermined",
        "fix": "none",
        "confidence": "medium",
        "escalate": False,
        "escalation_reason": "",
    }
    finding.update(overrides)
    return finding


def _good_result() -> dict[str, Any]:
    """A reference answer that should pass every check."""
    return {
        "fixture_id": "fx-01",
        "model": "claude-opus-5-5",
        "run": 1,
        "outcome": "completed",
        "cost_usd": 0.25,
        "served_models": ["claude-opus-5-5"],
        "tool_calls": [
            {"name": "list_findings", "input": {}},
            {"name": "get_finding", "input": {"finding_id": "fnd_1"}},
        ],
        "output": {
            "fixture_id": "fx-01",
            "audit_status": "investigated",
            "notes": "This covers browser requests only.",
            "findings": [
                _finding("fnd_1", "confirmed_violation", cited_request_ids=["req_a"]),
                _finding(
                    "fnd_2",
                    "requires_further_investigation",
                    cited_cookies=["_m"],
                    escalate=True,
                    escalation_reason="No request domains are known for this vendor.",
                ),
            ],
        },
    }


@pytest.fixture
def fixture(tmp_path: Path) -> Any:
    _write_fixture(tmp_path)
    return ft.load_fixture("fx-01", tmp_path)


def _score(fixture: Any, mutate: Any = None) -> Any:
    result = _good_result()
    if mutate:
        mutate(result)
    return sc.score_run(result, fixture)


def test_reference_answer_passes_every_check(fixture: Any) -> None:
    score = _score(fixture)
    assert score.passed
    assert not score.checks
    assert score.verdicts == {
        "fnd_1": ("confirmed_violation", False),
        "fnd_2": ("requires_further_investigation", True),
    }


def test_empty_answer_fails_instead_of_looking_clean(fixture: Any) -> None:
    score = _score(fixture, lambda r: r["output"].update(findings=[]))
    assert not score.passed
    assert score.checks["missing_findings"] == 2


def test_fabricated_request_id_fails_the_run(fixture: Any) -> None:
    def mutate(result: dict[str, Any]) -> None:
        result["output"]["findings"][0]["cited_request_ids"] = ["req_made_up"]

    score = _score(fixture, mutate)
    assert score.checks["fabricated_request_ids"] == 1
    assert not score.passed


def test_real_request_the_tools_never_returned_fails_the_run(fixture: Any) -> None:
    def mutate(result: dict[str, Any]) -> None:
        result["output"]["findings"][0]["cited_request_ids"] = ["req_b"]

    score = _score(fixture, mutate)
    assert score.checks["unseen_request_ids"] == 1
    assert score.checks["fabricated_request_ids"] == 0
    assert not score.passed


def test_request_returned_by_a_search_counts_as_seen(fixture: Any) -> None:
    def mutate(result: dict[str, Any]) -> None:
        result["tool_calls"].append(
            {
                "name": "query_evidence",
                "input": {
                    "url_contains": "",
                    "host_contains": "t.example",
                    "citable_only": False,
                    "max_results": 10,
                },
            }
        )
        result["output"]["findings"][0]["cited_request_ids"] = ["req_b", "req_old"]

    score = _score(fixture, mutate)
    assert score.checks["unseen_request_ids"] == 0
    # req_old is real and was returned, but it isn't from the opted-out load.
    assert score.checks["non_citable_request_ids"] == 1
    assert score.passed


def test_strong_verdict_without_citation_fails_the_run(fixture: Any) -> None:
    def mutate(result: dict[str, Any]) -> None:
        result["output"]["findings"][0]["cited_request_ids"] = []

    score = _score(fixture, mutate)
    assert score.checks["uncited_strong_verdicts"] == 1
    assert not score.passed


def test_coverage_checks_extra_and_duplicate_findings(fixture: Any) -> None:
    def mutate(result: dict[str, Any]) -> None:
        findings = result["output"]["findings"]
        findings.append(copy.deepcopy(findings[1]))
        findings.append(_finding("fnd_invented", "no_evidence_of_violation"))

    score = _score(fixture, mutate)
    assert score.checks["duplicate_findings"] == 1
    assert score.checks["extra_findings"] == 1
    assert not score.passed


def test_soft_checks_are_reported_without_failing(fixture: Any) -> None:
    def mutate(result: dict[str, Any]) -> None:
        unsettled = result["output"]["findings"][1]
        unsettled["cited_cookies"] = ["_not_in_finding"]
        unsettled["escalate"] = False
        result["output"]["findings"][0].update(escalate=True, escalation_reason=" ")

    score = _score(fixture, mutate)
    assert score.checks["unknown_cookies"] == 1
    assert score.checks["unsettled_not_escalated"] == 1
    assert score.checks["escalated_without_reason"] == 1
    assert score.passed


@pytest.mark.parametrize(
    "text",
    [
        "This is an illegal sale of data.",
        "The site violated the CCPA.",
        "The company will be fined.",
        "There is no server-side tracking on this site.",
        "Server-side tagging is not used here.",
    ],
)
def test_blocked_wording_is_flagged(fixture: Any, text: str) -> None:
    score = _score(fixture, lambda r: r["output"].update(notes=text))
    assert score.checks["blocked_wording"] >= 1


@pytest.mark.parametrize(
    "text",
    [
        "This evidence can't speak to server-side tracking.",
        "The pattern maps to an enforcement theme. That is risk mapping.",
        "The verdict is likely_violation, pending a re-test.",
    ],
)
def test_careful_wording_is_not_flagged(fixture: Any, text: str) -> None:
    score = _score(fixture, lambda r: r["output"].update(notes=text))
    assert score.checks["blocked_wording"] == 0


def test_incomplete_run_is_not_scored_as_an_answer(fixture: Any) -> None:
    score = _score(fixture, lambda r: r.update(outcome="max_tokens", output=None))
    assert not score.completed
    assert not score.passed
    assert not score.checks
    assert not score.verdicts


def test_failed_scan_must_be_reported_as_failed(tmp_path: Path) -> None:
    _write_fixture(tmp_path, scan_outcome="failed")
    failed = ft.load_fixture("fx-01", tmp_path)

    honest = _good_result()
    honest["output"].update(audit_status="scan_failed", findings=[])
    assert sc.score_run(honest, failed).passed

    pretended = sc.score_run(_good_result(), failed)
    assert pretended.checks["wrong_audit_status"] == 1
    assert pretended.checks["extra_findings"] == 1
    assert not pretended.passed


def _labels(tmp_path: Path, rows: list[tuple[str, str, str, str]]) -> Any:
    sheet = tmp_path / "labels.csv"
    header = "fixture,finding_id,status_today,kenneth_verdict,should_escalate\n"
    sheet.write_text(
        header + "".join(",".join(("fx-01", *row[:1], *row[1:])) + "\n" for row in rows)
    )
    return sc.load_labels(sheet)


def test_blank_labels_are_skipped_and_aliases_normalised(tmp_path: Path) -> None:
    labels = _labels(
        tmp_path,
        [
            ("fnd_1", "confirmed_violation", "Likely", "yes"),
            ("fnd_2", "requires_further_investigation", "", ""),
        ],
    )
    assert list(labels) == [("fx-01", "fnd_1")]
    assert labels[("fx-01", "fnd_1")] == {
        "verdict": "likely_violation",
        "escalate": True,
        "scanner_verdict": "confirmed_violation",
    }
    assert sc.load_labels(tmp_path / "missing.csv") == {}


def test_label_metrics(fixture: Any, tmp_path: Path) -> None:
    labels = _labels(
        tmp_path,
        [
            ("fnd_1", "confirmed_violation", "rfi", "yes"),
            ("fnd_2", "requires_further_investigation", "rfi", "yes"),
        ],
    )
    metrics = sc.label_metrics([_score(fixture)], labels)
    # The agent called fnd_1 confirmed, the label says unsettled.
    assert metrics["judged"] == 2
    assert metrics["agreement"] == 0.5
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["escalation_accuracy"] == 0.5
    assert metrics["scanner_agreement"] == 0.5
    assert metrics["majority_baseline"] == 1.0
    assert sc.label_metrics([_score(fixture)], {}) is None


def test_verdict_stability_needs_repeated_runs(fixture: Any) -> None:
    first = _score(fixture)
    assert sc.verdict_stability([first]) is None

    def flip(result: dict[str, Any]) -> None:
        result["run"] = 2
        result["output"]["findings"][0]["verdict"] = "likely_violation"

    assert sc.verdict_stability([first, _score(fixture, flip)]) == (1, 2)


def test_scorecard_and_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixtures = tmp_path / "fixtures"
    _write_fixture(fixtures)
    runs = tmp_path / "runs" / "claude-opus-5-5"
    runs.mkdir(parents=True)
    (runs / "fx-01.run1.json").write_text(json.dumps(_good_result()))
    (runs / "notes.json").write_text(json.dumps({"unrelated": True}))
    args = [
        str(tmp_path / "runs"),
        "--fixtures",
        str(fixtures),
        "--labels",
        str(tmp_path / "x.csv"),
    ]

    assert sc.main(args) == 0
    out = capsys.readouterr().out
    assert "Completed: 1 of 1" in out
    assert "Passed every evidence check: 1 of 1" in out
    assert "fabricated_request_ids: 0" in out
    assert "Label metrics: skipped" in out
    assert "Same verdict as the scanner: 2 of 2" in out

    bad = _good_result()
    bad["run"] = 2
    bad["output"]["findings"][0]["cited_request_ids"] = ["req_made_up"]
    (runs / "fx-01.run2.json").write_text(json.dumps(bad))
    cut_off = {**_good_result(), "run": 3, "outcome": "max_tokens", "output": None}
    (runs / "fx-01.run3.json").write_text(json.dumps(cut_off))

    assert sc.main(args) == 1
    out = capsys.readouterr().out
    assert "Completed: 2 of 3" in out
    assert "not scored, max_tokens: 1" in out
    assert "fx-01 run 2" in out
    assert "req_made_up" in out

    assert sc.main([str(tmp_path / "empty"), "--fixtures", str(fixtures)]) == 2
