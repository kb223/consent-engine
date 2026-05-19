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
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, HttpUrl

from consent_engine import __version__

app = FastAPI(
    title="consent-engine",
    version=__version__,
    description="Forensic consent compliance audit engine.",
)


class AuditRequest(BaseModel):
    url: HttpUrl


def _require_token(
    authorization: str | None = Header(default=None),
    x_consent_engine_token: str | None = Header(default=None),
) -> None:
    """Bearer-token gate for the audit endpoint.

    Reads ``CONSENT_ENGINE_API_TOKEN`` from the env. If unset, the server
    refuses to serve any POST to /audit at all — the unauthenticated default
    that shipped in v0.1.x–v0.4.x is closed in v0.5.0. Accepts the token via
    ``Authorization: Bearer <token>`` or ``X-Consent-Engine-Token: <token>``.
    """
    expected = os.environ.get("CONSENT_ENGINE_API_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail=(
                "CONSENT_ENGINE_API_TOKEN env var is not set on the server. "
                "The /audit endpoint is intentionally disabled without it. "
                "Set the token and restart the server to enable."
            ),
        )
    presented = None
    if authorization and authorization.lower().startswith("bearer "):
        presented = authorization[len("bearer ") :].strip()
    elif x_consent_engine_token:
        presented = x_consent_engine_token.strip()
    if presented is None or not secrets.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/audit", dependencies=[Depends(_require_token)])
async def audit(req: AuditRequest) -> dict[str, Any]:
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
        if bundle.scan_result.request_log:
            for entry in bundle.scan_result.request_log:
                f.write(json.dumps(entry.model_dump(mode="json"), default=str) + "\n")
        else:
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
    """`uvicorn` entrypoint for the FastAPI surface.

    Binds to ``127.0.0.1`` by default to keep the unauthenticated surface
    invisible to the network. Override with ``CONSENT_ENGINE_HOST`` (e.g.
    ``0.0.0.0`` behind a reverse proxy) only after setting
    ``CONSENT_ENGINE_API_TOKEN`` — without it, /audit returns 503.
    """
    import uvicorn

    host = os.environ.get("CONSENT_ENGINE_HOST", "127.0.0.1")
    port = int(os.environ.get("CONSENT_ENGINE_PORT", "8080"))
    uvicorn.run("consent_engine.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":                                        # pragma: no cover
    cli()
