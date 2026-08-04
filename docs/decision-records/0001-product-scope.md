# ADR 0001: Build a data-change assurance agent

- Status: Accepted
- Date: 2026-08-03

## Context

DataHub already provides search, lineage, and impact-analysis primitives. A
hackathon entry that simply restates those results would not demonstrate an
original agent or production-minded execution.

## Decision

EvidenceGraph will convert DataHub context into a governed change workflow:
multi-domain blast-radius analysis, evidence-backed risk ranking, executable
migration artifacts, deterministic validation, refusal behavior, and durable
write-back. The primary challenge category is Metadata-Aware Code Generation &
Development, with cross-cutting coverage of BI and production ML dependencies.

## Differentiation from the entrant's prior submission

The entrant's existing MandateGuard project detects transactional order/payment
mismatches and performs quarantine and reconciliation. EvidenceGraph is a new
codebase for a different problem: preventive change assurance before schema,
contract, pipeline, or ML feature changes are merged. It consumes change
proposals rather than bad business transactions and emits migration code and
test evidence rather than reconciliation actions.

## Consequences

- Generated sample artifacts are first-class judging material.
- The deterministic engine must remain useful without an LLM key.
- DataHub MCP observations and mutations must be visible in the evidence ledger.
- The product must fail closed when the context graph is incomplete.

