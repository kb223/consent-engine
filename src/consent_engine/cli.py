"""consent-engine CLI.

Usage:
    consent-engine audit <url> [--output-dir DIR]
    consent-engine chat <audit_id>
    consent-engine version

The `audit` command writes a full audit bundle (report.html, audit_result.json,
evidence.jsonl, deck.marp.md) to ./out/<audit_id>/.

The `chat` command opens a per-audit Claude conversation grounded in the
captured evidence + audit result + wiki context cited by the audit. Closes
the loop on Fred Pike's glass-box principle.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from consent_engine import __version__


def _audit_command(args: argparse.Namespace) -> int:
    """Run an audit against a URL. Writes the bundle to out/<audit_id>/."""
    # Lazy import so `--help` doesn't trigger Playwright load.
    from consent_engine.audit import run_audit

    url = args.url
    out_dir = Path(args.output_dir or "./out")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {url} (this takes ~30s)…", flush=True)
    bundle = asyncio.run(run_audit(url))

    audit_dir = out_dir / bundle.audit_id
    audit_dir.mkdir(parents=True, exist_ok=True)

    # Persist the network evidence per Fred Pike's "glass box" pattern —
    # every captured request goes to evidence.jsonl, audit-scoped.
    with (audit_dir / "evidence.jsonl").open("w") as f:
        for req in bundle.scan_result.network_requests:
            f.write(json.dumps(req.model_dump(mode="json"), default=str) + "\n")

    (audit_dir / "report.html").write_text(bundle.report_html)
    (audit_dir / "deck.marp.md").write_text(bundle.deck_marp_md)
    (audit_dir / "audit_result.json").write_text(
        json.dumps(bundle.audit_result.model_dump(mode="json"), indent=2, default=str)
    )
    (audit_dir / "executive_summary.md").write_text(bundle.executive_summary)

    findings = bundle.audit_result.findings
    print()
    print(f"Audit complete: {audit_dir}")
    print(f"  Report:    {audit_dir / 'report.html'}")
    print(f"  Deck:      {audit_dir / 'deck.marp.md'}")
    print(f"  Evidence:  {audit_dir / 'evidence.jsonl'}")
    print(f"  Findings:  {len(findings)} vendor finding(s)")
    return 0


def _chat_command(args: argparse.Namespace) -> int:
    """Open a Claude conversation grounded in a completed audit."""
    audit_dir = Path("./out") / args.audit_id
    if not audit_dir.exists():
        print(f"error: no audit bundle at {audit_dir}", file=sys.stderr)
        return 1

    try:
        from consent_engine.llm.client import chat_with_context
    except ImportError:
        print("error: chat requires `pip install consent-engine[chat]`", file=sys.stderr)
        return 1

    audit = json.loads((audit_dir / "audit_result.json").read_text())
    evidence_lines = (audit_dir / "evidence.jsonl").read_text().splitlines()

    print(
        f"Loaded audit {args.audit_id}. {len(evidence_lines)} network "
        f"events captured. Type 'exit' to quit.\n"
    )

    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not question or question.lower() in {"exit", "quit"}:
            return 0
        answer = chat_with_context(
            question=question,
            audit_result=audit,
            evidence=evidence_lines,
        )
        print(f"claude> {answer}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="consent-engine",
        description="Forensic consent compliance audit engine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Run an audit against a URL.")
    p_audit.add_argument("url", help="The URL to audit.")
    p_audit.add_argument("--output-dir", help="Output directory (default: ./out).")
    p_audit.set_defaults(func=_audit_command)

    p_chat = sub.add_parser("chat", help="Chat over a completed audit.")
    p_chat.add_argument("audit_id", help="Audit ID (the directory name under ./out/).")
    p_chat.set_defaults(func=_chat_command)

    p_ver = sub.add_parser("version", help="Print version + exit.")
    p_ver.set_defaults(func=lambda _: (print(f"consent-engine {__version__}"), 0)[1])

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
