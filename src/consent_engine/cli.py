"""consent-engine CLI.

Usage:
    consent-engine audit <url> [--variant signal|compliance]
                               [--monthly-ad-spend N] [--firm-name "Acme LLC"]
                               [--output-dir DIR]
    consent-engine render-deck <audit_id> [--output-dir DIR]
    consent-engine chat <audit_id>
    consent-engine version

Every audit runs two passes: primary S3 opt-out (consent denied via cookie
injection) + GPC (Sec-GPC: 1 header + navigator.globalPrivacyControl). The
pair lets the report distinguish CMP-honored opt-outs from CCPA/CPRA-
non-compliant sites that ignore the browser-level GPC signal.

`--variant signal --monthly-ad-spend N` activates the recoverable-revenue
math block (signal recovery framing for the CMO buyer). `--firm-name`
whitelabels the report.

The `audit` command writes a full audit bundle (report.html, audit_result.json,
evidence.jsonl, deck.marp.md) to ./out/<audit_id>/.

The `render-deck` command turns that deck.marp.md into a browsable deck.html
via @marp-team/marp-cli (shells out to `npx`; requires Node.js on PATH).

The `chat` command opens a per-audit Claude conversation grounded in the
captured evidence + audit result + wiki context cited by the audit. Closes
the loop on Fred Pike's glass-box principle.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
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

    firm_name = getattr(args, "firm_name", None)
    variant = getattr(args, "variant", "compliance")
    monthly_ad_spend = getattr(args, "monthly_ad_spend", None)
    print(f"Scanning {url} (two-pass S3 + GPC, ~60s)…", flush=True)
    bundle = asyncio.run(
        run_audit(
            url,
            with_gpc=True,
            firm_name=firm_name,
            report_variant=variant,
            monthly_ad_spend_usd=monthly_ad_spend,
        )
    )

    audit_dir = out_dir / bundle.audit_id
    audit_dir.mkdir(parents=True, exist_ok=True)

    # Persist the network evidence per Fred Pike's "glass box" pattern —
    # every captured request goes to evidence.jsonl, audit-scoped.
    with (audit_dir / "evidence.jsonl").open("w") as f:
        if bundle.scan_result.request_log:
            for entry in bundle.scan_result.request_log:
                f.write(json.dumps(entry.model_dump(mode="json"), default=str) + "\n")
        else:
            for url in bundle.scan_result.network_requests:
                f.write(json.dumps({"url": url}) + "\n")

    (audit_dir / "report.html").write_text(bundle.report_html)
    (audit_dir / "deck.marp.md").write_text(bundle.deck_marp_md)
    (audit_dir / "audit_result.json").write_text(
        json.dumps(bundle.audit_result.model_dump(mode="json"), indent=2, default=str)
    )
    (audit_dir / "executive_summary.md").write_text(bundle.executive_summary)

    findings = bundle.audit_result.findings
    confirmed = [f for f in findings if f.status == "confirmed_violation"]
    print()
    print(f"Audit complete: {audit_dir}")
    print(f"  Report:    {audit_dir / 'report.html'}")
    print(f"  Deck:      {audit_dir / 'deck.marp.md'}")
    print(f"  Evidence:  {audit_dir / 'evidence.jsonl'}")
    print(
        f"  Findings:  {len(findings)} vendor{'s' if len(findings) != 1 else ''}"
        f" ({len(confirmed)} confirmed violation{'s' if len(confirmed) != 1 else ''})"
    )
    if bundle.audit_result.gpc_tested:
        respected = bundle.audit_result.gpc_signal_respected
        verdict = (
            "respected" if respected
            else ("ignored" if respected is False else "inconclusive")
        )
        print(
            f"  GPC:       {verdict} "
            f"(baseline {bundle.audit_result.gpc_pixel_count_baseline} pixels → "
            f"{bundle.audit_result.gpc_pixel_count_with_gpc} under GPC)"
        )
    if bundle.audit_result.remediation:
        print(f"  Remediation: {len(bundle.audit_result.remediation)} step(s) in report")
    return 0


def _render_deck_command(args: argparse.Namespace) -> int:
    """Render an audit's deck.marp.md to deck.html via @marp-team/marp-cli."""
    audit_dir = Path(args.output_dir or "./out") / args.audit_id
    marp_md = audit_dir / "deck.marp.md"
    if not marp_md.exists():
        print(f"error: no deck.marp.md at {marp_md}", file=sys.stderr)
        return 1

    npx = shutil.which("npx")
    if not npx:
        print(
            "error: render-deck requires Node.js + npx on PATH.\n"
            "Install Node from https://nodejs.org/ then re-run, or render manually:\n"
            f"  npx --yes @marp-team/marp-cli@latest {marp_md} -o {audit_dir / 'deck.html'} --html",
            file=sys.stderr,
        )
        return 1

    deck_html = audit_dir / "deck.html"
    print(f"Rendering {marp_md} via @marp-team/marp-cli…", flush=True)
    try:
        subprocess.run(
            [
                npx, "--yes", "@marp-team/marp-cli@latest",
                str(marp_md), "-o", str(deck_html), "--html",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"error: marp-cli exited {e.returncode}", file=sys.stderr)
        return 1
    print(f"Deck rendered: {deck_html}")
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
    p_audit.add_argument(
        "--with-gpc",
        action="store_true",
        help="[deprecated, always on] kept for backward compatibility.",
    )
    p_audit.add_argument(
        "--firm-name",
        dest="firm_name",
        help="Customer firm name to render at the top of the report (whitelabel).",
    )
    p_audit.add_argument(
        "--variant",
        choices=("compliance", "signal"),
        default="compliance",
        help="Report variant: 'compliance' (legal/risk framing) or 'signal' "
        "(growth/recovery framing with dollar math). Default: compliance.",
    )
    p_audit.add_argument(
        "--monthly-ad-spend",
        dest="monthly_ad_spend",
        type=int,
        help="Self-reported monthly ad spend in USD. Activates per-vendor signal "
        "recovery math in the signal-variant report. Example: --monthly-ad-spend 50000",
    )
    p_audit.set_defaults(func=_audit_command)

    p_render = sub.add_parser(
        "render-deck",
        help="Render an audit deck.marp.md to deck.html via @marp-team/marp-cli.",
    )
    p_render.add_argument("audit_id", help="Audit ID (the directory name under ./out/).")
    p_render.add_argument("--output-dir", help="Output directory (default: ./out).")
    p_render.set_defaults(func=_render_deck_command)

    p_chat = sub.add_parser("chat", help="Chat over a completed audit.")
    p_chat.add_argument("audit_id", help="Audit ID (the directory name under ./out/).")
    p_chat.set_defaults(func=_chat_command)

    p_ver = sub.add_parser("version", help="Print version + exit.")
    p_ver.set_defaults(func=lambda _: (print(f"consent-engine {__version__}"), 0)[1])

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
