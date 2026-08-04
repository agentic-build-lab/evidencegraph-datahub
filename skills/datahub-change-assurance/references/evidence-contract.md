# Evidence contract

## Observation states

- `observed`: the interface returned the fact and its payload hash is recorded.
- `absent`: a successful, exhaustive query returned no matching fact.
- `not_queried`: the collector did not attempt the required operation.
- `read_failed`: the operation returned an error or timed out.
- `incomplete`: pagination or the lineage frontier was not exhausted.
- `unsupported`: the selected interface cannot represent the entity or aspect.
- `contradicted`: two observations cannot both be true under the same revision.

Only `observed` facts may support exact generated code. Derived claims must name their source observation IDs and deterministic derivation.

## Public-claim limits

- Say “DataHub MCP” only for operations actually performed through the official MCP server.
- Label SDK aspect enrichment separately.
- Say “validated” only when the required native tool ran and returned a passing receipt.
- Say “write-back verified” only after per-target readback.
- Do not equate a deterministic fixture replay with a live DataHub query.
- Do not claim graph closure until a newer post-migration snapshot is collected and compared.
