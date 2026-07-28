"""consent-engine — forensic consent compliance audit engine.

Public package surface:
- consent_engine.cli            CLI entrypoint (`consent-engine audit ...`)
- consent_engine.mcp_server     MCP server entrypoint (`consent-engine-mcp`)
- consent_engine.tools.*        Eight deterministic audit tools
- consent_engine.models.*       Pydantic models (AuditResult, ScanResult, ...)
- consent_engine.llm.client     LiteLLM-wrapped chat surface (agentic layer)
"""

# Silence LiteLLM's startup probes for providers the user hasn't configured
# (Bedrock / SageMaker / Vertex AI) before litellm imports anywhere downstream.
# These warnings are harmless when the user is on Anthropic or OpenAI, but they
# emit a noisy stderr block on every audit run via uvx.
import os as _os

_os.environ.setdefault("LITELLM_LOG", "ERROR")
_os.environ.setdefault("LITELLM_DROP_PARAMS", "true")

# Read the version from installed package metadata so `pyproject.toml` stays the
# single source of truth. Hardcoding it here previously meant a release could
# ship with `consent-engine version` reporting the prior number.
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError  # noqa: E402
from importlib.metadata import version as _dist_version  # noqa: E402

try:
    __version__ = _dist_version("consent-engine")
except _PackageNotFoundError:  # pragma: no cover - source tree with no install
    __version__ = "0.0.0+unknown"
