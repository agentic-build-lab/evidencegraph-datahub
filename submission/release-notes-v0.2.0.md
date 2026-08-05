# EvidenceGraph v0.2.0

EvidenceGraph v0.2.0 introduces Assurance Studio, an evidence-bound public
replay that shows how DataHub changes both the blast radius an agent can see
and the authority it is allowed to exercise.

## Highlights

- Compares a 3-of-7 repository-only baseline with a 7-of-7 DataHub-grounded
  impact graph over the same declared synthetic universe.
- Traverses datasets, a data job, a dashboard, an ML feature, a model, and a
  production model deployment with claim-level source bindings.
- Produces a nine-file migration pack spanning SQL, dbt, a unified diff,
  validation, orchestration, ML compatibility, a migration plan, and a
  machine-readable manifest.
- Reports the exact fourteen-gate composition: one integrity gate, eight
  structured-file parsers, and five native or integration gates.
- Demonstrates the complete-versus-missing-lineage authority switch: complete
  evidence permits reviewable proposals; incomplete evidence caps confidence,
  quarantines drafts, and produces zero write-back proposals.
- Includes recorded, readback-verified controlled local DataHub write-back receipts, an
  immediate stateless retry with three verified no-ops, and a separately
  labeled deterministic closure replay.

## Evidence boundaries

The hosted Assurance Studio is a read-only replay over repository-owned
evidence and exposes no DataHub credential or mutation endpoint. Recorded
write-back receipts come from a controlled, explicitly approved local DataHub run. Fresh
graph closure is claimed only for the labeled deterministic before/after
replay, and the 7-of-7 measurement is scoped to the declared synthetic graph.

## Verification and security

- Python 3.11 and 3.12 install from `uv.lock` and run Ruff, strict mypy, and the
  full pytest suite.
- The public replay installs from `package-lock.json`, passes high-severity npm
  audit, ESLint, a production build, and rendered-page tests.
- Gitleaks scans complete reachable history and a clean release tree using a
  digest-pinned container image.
- Standalone narration and DOVA-SYNDROME music files are excluded from release
  assets; the final mixed MP4 and published checksums are the only video
  deliverables.
