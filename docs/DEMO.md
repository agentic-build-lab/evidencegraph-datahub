# EvidenceGraph Demo Guide

EvidenceGraph offers two deliberately distinct demo paths:

1. a deterministic fixture run that needs no DataHub credentials; and
2. a local live-integration run that reads from DataHub Core through the
   official DataHub MCP Server.

The [public judge experience](https://evidencegraph-datahub.liu891855.chatgpt.site) is a
deterministic, no-login replay. It exposes no mutation endpoint; the separate frozen MCP trace
is the local live DataHub integration proof.

## Flagship scenario

The proposal removes `customer_tier` from the synthetic Postgres dataset
`commerce.raw_orders`. The declared downstream test universe contains seven
affected assets:

- two dbt datasets;
- one Airflow data job;
- one Looker dashboard;
- one ML feature;
- one ML model; and
- one production model deployment.

A repository-only view finds 3 of 7 assets. The DataHub-grounded view finds all
7 of 7, recovering the dashboard and all three ML-side consumers. EvidenceGraph
then emits nine migration artifacts and runs fourteen validation gates.

## Fast deterministic run

Prerequisites: Python 3.11 or 3.12. Docker is required for the verified
official Airflow container path on Windows; native Airflow execution is
unsupported there, so Windows without the pinned image fails that gate closed.
WSL2 and Linux can use the locked native environment.

```bash
uv sync --all-extras --locked --python 3.12
uv run --no-sync evidencegraph demo --output outputs/demo
uv run --no-sync evidencegraph ablation
```

Expected release-candidate results on Linux, WSL2, or Windows with the pinned
Airflow image available:

- 7 downstream impacts;
- 9 generated artifacts;
- 14 of 14 validators passed;
- dbt Core 1.12.0 built the generated model and passed 7 of 7 tests;
- the generated Airflow DAG passed DagBag import and dependency-gate
  assertions in the official `apache/airflow:3.3.0-python3.12` container; and
- repository-only recall was 3 of 7 versus 7 of 7 with DataHub context.

The generated bundle is written under the selected output directory. Inspect
`SUMMARY.md`, `evidence-ledger.json`, and the `migration/` directory together;
the human-readable summary is not a substitute for the ledger.

## Local DataHub integration

Prerequisites: Docker, a local DataHub Core v1.6.0 Quickstart, Node.js for the
MCP server package, and the Python DataHub dependencies.

```bash
uv sync --all-extras --locked --python 3.12
uv run --no-sync python scripts/bootstrap_datahub.py --gms-url http://localhost:8080
uv run --no-sync python scripts/verify_mcp.py \
  --gms-url http://localhost:8080 \
  --output outputs/mcp-verification.json
uv run --no-sync evidencegraph analyze-live \
  --change fixtures/changes/drop_customer_tier.json \
  --gms-url http://localhost:8080 \
  --output outputs/live
```

This path uses `mcp-server-datahub@0.6.0` for search, entity context, schema,
dataset lineage, and column-lineage collection. A narrow DataHub Python SDK
reader enriches aspects that MCP Server 0.6.0 does not expose as lineage nodes,
including the modeled ML deployment relationship.

## Controlled metadata write-back

Write-back is never required for the read-only demo. In a disposable local
DataHub instance, it requires all three conditions:

1. the CLI receives `--apply`;
2. `EVIDENCEGRAPH_ENABLE_WRITES=true`; and
3. the MCP server exposes mutation tools.

The allowlist contains tag addition, description append, and evidence-document
save operations. A verified local run applied those three operations and read every resulting
state back. A new MCP client retried the identical proposal set and verified three no-ops,
including reuse of the same document URN. Separately, the deterministic before/after fixture
replay exercises the closure protocol: stale context is refused, and a newer complete graph
with zero old-field consumers closes.

## Refusal behavior

EvidenceGraph refuses safe-to-merge and write-back decisions when required
lineage is incomplete, a changed field cannot be established, a critical owner
is absent, evidence conflicts, or a required validator fails. Refusal keeps the
available evidence and names the next safe action.

## Public links

- Live demo: `https://evidencegraph-datahub.liu891855.chatgpt.site`
- Repository: `https://github.com/agentic-build-lab/evidencegraph-datahub`
- Sample evidence package: `https://github.com/agentic-build-lab/evidencegraph-datahub/tree/main/examples`
- Video: `https://youtu.be/MFDSc8Nx1Qs`
