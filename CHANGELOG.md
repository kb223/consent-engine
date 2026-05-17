# Changelog

All notable changes to consent-engine. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-16 — initial public release

### Added
- Eight-tool deterministic audit pipeline:
  - tool_01 GTM container parser (live interception or JSON upload)
  - tool_02 violation classifier (S2 inconclusive vs S3 definitive)
  - tool_03 Playwright browser scanner with consent state pre-set
  - tool_04 HAR analyzer
  - tool_05 vendor library lookup (custom + Open Cookie Database)
  - tool_06 server-side GTM detector
  - tool_06b out-of-GTM pixel detector
  - tool_07 markdown wiki retriever (no vector DB)
  - tool_08 report + Marp deck generator (LLM exec summary only)
- CLI: `consent-engine audit <url>` + `consent-engine chat <audit_id>`
- MCP server: `consent-engine-mcp` (Claude Desktop / Code integration)
- Claude Code skill at `.claude/skills/consent-audit/SKILL.md`
- Evals harness skeleton at `evals/` with golden-case YAML format
- Glass-box reporting: every captured network request persisted to
  `evidence.jsonl` per audit, queryable from CLI + MCP
- Lawsuit-surge knowledge base page at
  `data/wiki/enforcement/lawsuit-surge.md`
- End-to-end scenarios doc at `docs/scenarios.md` with Mermaid diagram

### Design decisions
- Deterministic by default. LLM scoped to executive-summary generation
  only. Credit to Fred Pike (MeasureSummit May 2026) for the explicit
  framing.
- Markdown wiki replaces vector DB. Karpathy LLM-wiki pattern. Zero
  embeddings, zero Pinecone, zero fine-tuning. The whole knowledge layer
  is version-controlled markdown.
- Multi-tier vendor library: custom legally-annotated entries take
  precedence, then the Open Cookie Database (~3,200 entries), then
  flagged for manual review.
