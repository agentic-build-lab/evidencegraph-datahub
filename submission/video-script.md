# EvidenceGraph Demo Video Script

**Final duration:** 2:30
**Format:** 1920×1080, 30 fps, English narration and captions
**Voice:** Kokoro `af_heart`, generated offline
**Public URL:** `<PUBLIC_VIDEO_URL>`

## 0:00–0:14 — The change is not the incident

> A schema change should not become an incident. Before anyone merges it,
> EvidenceGraph asks a harder question: what will this change actually break?

## 0:14–0:34 — Repository context is incomplete

> Repository search finds three of seven downstream consumers. It misses the
> dashboard, the machine-learning feature, the model, and the production
> deployment. That is a forty-two point nine percent view — and a false-safe
> recall — and a false-safe decision waiting to happen.

## 0:34–0:53 — Make the context graph executable

> EvidenceGraph reads DataHub through the official MCP server and the Python
> SDK. Schemas, ownership, lineage, contracts, tags, documentation, dashboards,
> and machine-learning metadata become one executable context graph.

## 0:53–1:14 — Recover the complete blast radius

> Now the blast radius is complete: two dbt models, an Airflow job, an executive
> dashboard, an ML feature, a model, and its production deployment. Each path is
> routed to its owner, prioritized, and linked to the exact DataHub object that
> supports it.

## 1:14–1:34 — Compile migration, not advice

> EvidenceGraph does not stop at an explanation. It compiles nine concrete
> artifacts: SQL, dbt model and tests, validation queries, an Airflow evidence
> gate, an ML contract, a migration plan, and a real unified diff that Git can
> apply cleanly.

## 1:34–1:56 — Evidence before action

> Fourteen deterministic gates run in their native environments: DuckDB, dbt
> Core, the official Airflow container, feature-parity checks, and Git patch
> application. All fourteen pass. Remove one lineage page, and EvidenceGraph
> refuses the safe-to-merge verdict and blocks every mutation.

## 1:56–2:18 — Write back, retry, and close

> With explicit approval, three scoped results write back into DataHub and
> verify by readback. A new client retries the same plan: three verified no-ops,
> no duplicates. In the deterministic closure replay, EvidenceGraph requires a
> newer complete graph and closes only when the retired field has zero remaining
> consumers.

## 2:18–2:30 — Inspect every claim

> EvidenceGraph makes DataHub's context graph operational. Inspect the public
> replay, audit every claim in the evidence ledger, and run the complete
> open-source system yourself.
