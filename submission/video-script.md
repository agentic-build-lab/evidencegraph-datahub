# EvidenceGraph Demo Video Script

- **Target duration:** 2:10
- **Format:** 1920 x 1080, 30 fps
- **Narration:** Kokoro `af_heart`, 1.05x
- **Captions:** Phrase-level, one or two lines, no word-by-word highlighting
- **Music:** "A Little Story" by Kei Morimoto, used under the DOVA-SYNDROME license

**Final public URL:** https://youtu.be/qnPR0Y6kENE

## 0:00-0:10 — The change is not the incident

> A schema change should not become an incident. EvidenceGraph, an autonomous
> assurance agent, asks before merge: what will this change actually break?

The film opens on the proposed removal of `customer_tier`, then expands from a
single diff into the assurance question that drives the product.

## 0:09-0:25 — Repository context is incomplete

> In our frozen synthetic seven-consumer truth set, repository search finds
> only three. It misses the dashboard, machine-learning feature, model, and
> deployment: a 42.9 percent view, and a false-safe decision.

The visual compares the repository-only result with the frozen seven-asset
truth set. Four DataHub-only consumers remain invisible to code search.

## 0:25-0:41 — Make the context graph executable

> EvidenceGraph reads DataHub through the official MCP server and Python SDK.
> Schemas, ownership, lineage, contracts, dashboards, and ML metadata form an
> executable graph controlling scope, plans, and authority.

The official interfaces are shown as an operational boundary, followed by the
heterogeneous context they make available to the assurance workflow.

## 0:41-0:59 — Ground all seven declared truth-set impacts

> Against that frozen truth set, DataHub grounds all seven impacts: two dbt
> models, Airflow, a dashboard, an ML feature, model, and deployment. Every path
> carries its owner, priority, and exact source object.

The graph resolves all seven affected assets, including the dashboard and ML
chain that repository search missed.

## 0:58-1:17 — Compile migration, not advice

> EvidenceGraph compiles nine pull-request-ready drafts for human review, never
> auto-merged: SQL, dbt model and tests, validation queries, an Airflow evidence
> gate, an ML contract, migration plan, and a real unified diff.

Real source excerpts and the generated manifest establish that the output is a
reviewable migration pack, not generic prose.

## 1:17-1:35 — Evidence changes authority

> Fourteen deterministic gates run in DuckDB, dbt Core, the official Airflow
> container, feature-parity checks, and Git patch application. All pass. Remove
> one lineage page, and EvidenceGraph revokes proposal authority and blocks
> every mutation.

The interface exposes the exact composition: one integrity gate, eight parse
gates, patch application, DuckDB parity, dbt build and tests, Airflow DagBag,
and ML parity. The same nine drafts change from `PROPOSAL ALLOWED` to
`QUARANTINED`, while write-back proposals fall to zero when the context frontier
is incomplete.

## 1:35-1:57 — Governed write-back and closure

> With explicit approval in a controlled local DataHub run, a tag, description,
> and evidence document write back and verify by readback. A fresh client retries them: three verified
> no-ops, zero duplicates. A labeled closure replay closes only on a newer
> complete graph with zero retired-field consumers.

The sequence separates applied-and-verified mutations, immediate stateless
retry idempotence, and the labeled deterministic closure replay.

## 1:56-2:10 — Inspect every claim

> EvidenceGraph turns DataHub into an observe, plan, validate, refuse-or-act
> loop. In the public deterministic replay, audit each claim, source object,
> confidence, test receipt, and unresolved risk.

The closing sequence records the public Assurance Studio replay and evidence
ledger, then resolves to a clean-clone command, deterministic receipts, public
demo URL, and repository calls to action.

## Music credit

"A Little Story" by Kei Morimoto. Source and license details are preserved in
[`videos/evidencegraph-launch/MUSIC_CREDITS.md`](../videos/evidencegraph-launch/MUSIC_CREDITS.md).
