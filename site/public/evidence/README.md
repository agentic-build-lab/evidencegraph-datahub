# EvidenceGraph example evidence

This package is a public, synthetic-data evidence replay. The flagship ledger was collected from
local DataHub OSS v1.6.0 through the official `mcp-server-datahub@0.6.0`, with explicitly labeled
Python SDK aspect enrichment for MCP gaps.

## Measured result

- Full DataHub context: **7/7 affected assets (100% recall)**.
- Repository-only context: **3/7 (42.9% recall)**.
- Improvement: **+57.1 percentage points**; the hidden BI and ML consumers are recovered.
- Migration bundle: **9 artifacts** across SQL, dbt, Airflow, ML, plan,
  manifest, and a real unified diff.
- Validation: **14/14 passed**—one integrity/evidence-binding check, eight
  structured-file parser checks, and five native or integration checks across
  Git patch application, DuckDB parity, dbt build, official Airflow 3.3.0
  container import/gate execution, and ML parity.
- Separate approved DataHub run: **3/3 applied and read back**; an immediate
  stateless retry was **3/3 verified no-op**.

## Inspect in order

1. [Proposal](flagship/proposal.json) and independent [truth manifest](flagship/truth-manifest.json)
2. [Ablation](ablation/comparison.json)
3. [Live sanitized context](flagship/context-snapshot.live.sanitized.json)
4. [Evidence ledger](flagship/evidence-ledger.live.sanitized.json)
5. [Migration pack](flagship/migration/) and [native receipts](flagship/validation-receipts.json)
6. [MCP observations](flagship/mcp-trace.sanitized.json)
7. [Write-back receipts](flagship/writeback-receipts.json) and
   [idempotent retry](flagship/writeback-retry-receipts.json)
8. [Fail-closed refusal](refusal/incomplete-lineage-ledger.json)
9. Deterministic replay [before graph](closure/before-graph.json),
   [after graph](closure/after-graph.json), and [closure receipt](closure/closure-receipt.json)

The closure package is a deterministic fixture replay, not a claim that the public static demo
mutates a hosted DataHub instance.
