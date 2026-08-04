# DataHub Hackathon Feedback

Prepared for the optional feedback-prize fields from the final EvidenceGraph
build.

## Which features felt polished?

The separation between DataHub Core, the official MCP Server, and the Python
SDK made it possible to build a clear trust boundary. MCP tool discovery and
named read versus mutation tools were especially useful for a safety-sensitive
agent. DataHub's common URN model also let one evidence ledger cover datasets,
jobs, dashboards, ML features, models, deployments, owners, contracts, tags,
and documents without inventing a parallel identity system.

Column-lineage queries, entity retrieval, and governed document/tag/description
mutations combined into a coherent read-reason-act workflow. The ability to
write an evidence document back to the context graph was more valuable than a
one-time report because future operators can discover the decision where they
already investigate the asset.

## Where did setup or integration consume unnecessary time?

The main friction was establishing an explicit compatibility matrix across the
DataHub Core image, Python SDK package, and MCP server package. It would help if
the Quickstart documentation published a single agent-development matrix with
known-compatible versions, required environment variables, mutation flags,
health checks, and a minimal end-to-end MCP smoke test.

MCP response shapes also vary by tool and entity type. More small, versioned
examples for pagination, column lineage, document search/save, and mixed entity
retrieval would reduce normalization work. Clearer guidance on when `hasMore`,
offsets, token-budget truncation, or an empty result should be treated as
incomplete would be valuable for agents that must fail closed.

## What future engineering work would be most valuable?

1. A standard MCP evidence envelope containing tool version, observation time,
   pagination state, permission state, truncation reason, response digest, and
   source URNs.
2. Stable client-provided idempotency keys for mutation tools, plus documented
   create-or-update semantics and read-after-write examples.
3. First-class lineage traversal that treats datasets, dashboards, charts, ML
   features, models, and deployments uniformly while preserving field-level
   paths.
4. A change-proposal primitive that can relate a proposed schema or contract
   revision to affected assets, owners, validation receipts, and a final
   decision.
5. A disposable agent test harness that seeds a small heterogeneous graph and
   asserts MCP behavior across releases.

## What bugs or unexpected behavior did you encounter?

The most important unexpected limitation was that MCP Server 0.6.0 did not
expose the modeled ML model deployment relationship as a lineage node in the
same way as dataset and dashboard consumers. EvidenceGraph therefore uses a
narrow Python SDK aspect reader for that relationship and records the
enrichment explicitly instead of presenting it as MCP lineage.

We also found that a successful tool response or an empty page is not enough to
prove traversal completeness without interpreting pagination and truncation
signals. This may be expected behavior rather than a defect, but agent-oriented
documentation should make the distinction prominent because a metadata browser
can tolerate partial results while an autonomous change decision cannot.

Public issue links: none filed. The observations above are product feedback and
compatibility notes, not claims that an organizer-confirmed defect exists.
