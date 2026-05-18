"""Stripped FastAPI surface for the public consent-engine.

Single endpoint: POST /audit
  - Accepts { "url": "https://example.com" }
  - Returns the audit_result.json contents inline + a link to the report
    bundle on disk (relative path).

For the full async / job-queue flow the private business app uses, fork this
file. This public version is deliberately small and synchronous so it's easy
to read.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from consent_engine import __version__

app = FastAPI(
    title="consent-engine",
    version=__version__,
    description="Forensic consent compliance audit engine.",
)


class AuditRequest(BaseModel):
    url: HttpUrl


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/audit")
async def audit(req: AuditRequest) -> dict:
    """Run a full audit and return the structured result inline.

    For long-running jobs swap this for an async job-queue (BackgroundTasks
    or a real queue like Celery/Arq).
    """
    from consent_engine.audit import run_audit

    try:
        bundle = await run_audit(url=str(req.url))
    except Exception as e:                                       # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"audit failed: {e}") from e

    out_dir = Path("./out") / bundle.audit_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "evidence.jsonl").open("w") as f:
        for url in bundle.scan_result.network_requests:
            f.write(json.dumps({"url": url}) + "\n")
    (out_dir / "report.html").write_text(bundle.report_html)
    (out_dir / "deck.marp.md").write_text(bundle.deck_marp_md)
    (out_dir / "audit_result.json").write_text(
        json.dumps(bundle.audit_result.model_dump(mode="json"), indent=2, default=str)
    )
    (out_dir / "executive_summary.md").write_text(bundle.executive_summary)

    return {
        "audit_id": bundle.audit_id,
        "bundle": str(out_dir),
        "result": bundle.audit_result.model_dump(mode="json"),
    }


def cli() -> None:
    """`uvicorn` entrypoint for the FastAPI surface."""
    import uvicorn
    uvicorn.run("consent_engine.api:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":                                        # pragma: no cover
    cli()
