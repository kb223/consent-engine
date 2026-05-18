"""consent-engine — forensic consent compliance audit engine.

Public package surface:
- consent_engine.cli            CLI entrypoint (`consent-engine audit ...`)
- consent_engine.mcp_server     MCP server entrypoint (`consent-engine-mcp`)
- consent_engine.tools.*        Eight deterministic audit tools
- consent_engine.models.*       Pydantic models (AuditResult, ScanResult, ...)
- consent_engine.llm.client     LiteLLM-wrapped chat surface (agentic layer)
"""

__version__ = "0.4.0"
