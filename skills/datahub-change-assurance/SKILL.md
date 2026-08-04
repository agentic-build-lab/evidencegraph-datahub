---
name: datahub-change-assurance
description: Assess proposed schema, contract, pipeline, or ML feature changes with DataHub context; map downstream impact across data, orchestration, BI, and ML; generate evidence-linked migration artifacts; run deterministic validation gates; and propose governed DataHub write-backs. Use for blast-radius analysis, breaking-change reviews, migration planning, or go/no-go decisions where incomplete lineage must fail closed.
---

# DataHub Change Assurance

Turn a proposed change into a bounded EvidenceGraph run. Treat DataHub as the operational context graph: its schema, field lineage, ownership, contracts, documents, BI metadata, and ML metadata must change the decision or generated artifacts.

## Workflow

1. Normalize the proposal into a `ChangeRequest`. Reject an empty identifier, invalid DataHub URN, or a column change without the required field and replacement/type details.
2. Prefer live collection with the pinned official DataHub MCP server. Use SDK aspect reads only for fields the MCP surface cannot return, and label each observation with its interface.
3. Prove collection completeness before generation. Distinguish an observed absence from not queried, read failure, truncation, and unsupported metadata.
4. Propagate impact along explicit asset and field lineage. Do not infer exact column impact from dataset-only lineage.
5. Rank consumers, route owners, and create claim-level evidence references.
6. Generate only allowlisted, deterministic migration strategies. Reject metadata-derived SQL identifiers or mappings outside the validated contract.
7. Run every required validator. Treat failed or skipped required checks as a no-go decision.
8. Emit the evidence ledger before considering mutation.
9. Keep DataHub write-back in proposal mode unless the user explicitly requests it, `EVIDENCEGRAPH_ENABLE_WRITES=true`, mutation tools are available, and every safety gate passed.
10. For live writes, restrict targets to the configured scope tag, verify the approved target digest, mutate through the allowlist, and read every result back.

## Commands

From the EvidenceGraph repository root:

```powershell
evidencegraph demo --output outputs/demo
evidencegraph ablation
evidencegraph analyze-live --change fixtures/changes/drop_customer_tier.json
```

For an explicitly approved synthetic write-back:

```powershell
$env:EVIDENCEGRAPH_ENABLE_WRITES = "true"
evidencegraph analyze-live --change fixtures/changes/drop_customer_tier.json --apply
```

Never put tokens on a command line. Read `DATAHUB_GMS_TOKEN` from the environment, pass only a minimal environment to child processes, and require HTTPS for remote DataHub hosts.

## Required output

Return:

- the changed producer and normalized proposal;
- all evidenced downstream paths and affected fields;
- risk-ranked consumers and observed owners;
- an ordered migration plan;
- generated artifact hashes and claim bindings;
- validator command, tool version, exit status, output hash, and result;
- unresolved risks and an explicit go/no-go decision;
- write-back proposals and verified receipts when execution was authorized.

Use the state definitions and public-claim limits in [references/evidence-contract.md](references/evidence-contract.md).

## Refusal rules

Refuse exact artifact generation or mutation when lineage is incomplete, the source field is unobserved, direct field mapping is absent, a high-risk consumer is unowned, an evidence claim is unresolved or contradicted, required validation does not pass, a write target falls outside scope, or a write cannot be read back.
