# EvidenceGraph Demo Video Script

- **Target duration:** 2:10
- **Format:** 1920 x 1080, 30 fps
- **Narration:** Kokoro `af_heart`, 1.02x
- **Captions:** Phrase-level, one or two lines, no word-by-word highlighting
- **Music:** "A Little Story" by Kei Morimoto, used under the DOVA-SYNDROME license

**Final public URL:** Added after final preview approval, render, and upload

## 0:00-0:10 — The change is not the incident

> A schema change should not become an incident. Before anyone merges it,
> EvidenceGraph asks a harder question: what will this change actually break?

The film opens on the proposed removal of `customer_tier`, then expands from a
single diff into the assurance question that drives the product.

## 0:09-0:25 — Repository context is incomplete

> Repository search finds three of seven downstream consumers. It misses the
> dashboard, the machine-learning feature, the model, and the production
> deployment. That is a 42.9 percent view — and a false-safe decision waiting
> to happen.

The visual compares the repository-only result with the frozen seven-asset
truth set. Four DataHub-only consumers remain invisible to code search.

## 0:25-0:41 — Make the context graph executable

> EvidenceGraph reads DataHub through the official MCP server and the Python
> SDK. Schemas, ownership, lineage, contracts, tags, documentation, dashboards,
> and machine-learning metadata become one executable context graph.

The official interfaces are shown as an operational boundary, followed by the
heterogeneous context they make available to the assurance workflow.

## 0:41-0:59 — Recover the complete blast radius

> Now the blast radius is complete: two dbt models, an Airflow job, an executive
> dashboard, an ML feature, a model, and its production deployment. Each path is
> routed to its owner, prioritized, and linked to the exact DataHub object that
> supports it.

The graph resolves all seven affected assets, including the dashboard and ML
chain that repository search missed.

## 0:58-1:17 — Compile migration, not advice

> EvidenceGraph does not stop at an explanation. It compiles nine concrete
> artifacts: SQL, dbt model and tests, validation queries, an Airflow evidence
> gate, an ML contract, a migration plan, and a real unified diff that Git can
> apply cleanly.

Real source excerpts and the generated manifest establish that the output is a
reviewable migration pack, not generic prose.

## 1:17-1:35 — Evidence changes authority

> Fourteen deterministic gates: DuckDB, dbt Core, the official Airflow
> container, feature-parity checks, and Git patch application. All fourteen
> pass. Remove one lineage page, and EvidenceGraph refuses the safe-to-merge
> verdict and blocks every mutation.

The interface exposes the exact composition: one integrity gate, eight parse
gates, patch application, DuckDB parity, dbt build and tests, Airflow DagBag,
and ML parity. The same nine drafts change from `PROPOSAL ALLOWED` to
`QUARANTINED`, while write-back proposals fall to zero when the context frontier
is incomplete.

## 1:35-1:57 — Governed write-back and closure

> With explicit approval, three scoped results write back into DataHub and
> verify by readback. A new client retries the same plan: three verified no-ops,
> no duplicates. In the deterministic closure replay, EvidenceGraph requires a
> newer complete graph and closes only when the retired field has zero remaining
> consumers.

The sequence separates applied-and-verified mutations, immediate stateless
retry idempotence, and the labeled deterministic closure replay.

## 1:56-2:10 — Inspect every claim

> EvidenceGraph makes DataHub's context graph operational. Inspect the public
> replay, audit every claim in the evidence ledger.

The closing sequence records the public Assurance Studio replay and evidence
ledger, then resolves to a clean-clone command, deterministic receipts, public
demo URL, and repository calls to action.

## Music credit

"A Little Story" by Kei Morimoto. Source and license details are preserved in
[`videos/evidencegraph-launch/MUSIC_CREDITS.md`](../videos/evidencegraph-launch/MUSIC_CREDITS.md).
