# consent-engine v0.5.0 — Release artifacts

> FDE-portfolio public-release artifacts. Tagged 2026-05-18.

This folder is the auditable record of how v0.5.0 was hardened. Every claim in the [v0.5.0 CHANGELOG entry](../../CHANGELOG.md) traces back to a document here.

## Contents

| File | What's in it |
|---|---|
| [`security-audit.md`](security-audit.md) | Internal security audit punch list (HIGH/MED/LOW). All HIGH + MED items closed in v0.5.0. |
| [`cve-scan.md`](cve-scan.md) | Dependency CVE posture as of 2026-05-18. |
| [`type-coverage.md`](type-coverage.md) | mypy strict run output + accepted-warnings list with rationale. |
| [`e2e-smoke-test.md`](e2e-smoke-test.md) | End-to-end smoke test results against `https://example.com`. |
| [`jurisdiction-validation.md`](jurisdiction-validation.md) | Validation matrix proving jurisdiction detection works for US / UK / Canada / EU / Quebec-French sites. |

## How this folder gets used

When a reviewer (FDE-portfolio assessor, OSS contributor, security researcher) lands on the repo cold and wants to evaluate release quality, this folder is the auditable record.

The [SECURITY.md](../../SECURITY.md) file at repo root has the policy + threat model. This folder has the proof of work behind it.
