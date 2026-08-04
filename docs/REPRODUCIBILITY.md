# Reproducibility

EvidenceGraph separates deterministic replay, native artifact validation, and
live DataHub integration so each claim has a visible evidence boundary.

## Verified environment

The current release-candidate evidence was produced with:

| Component | Verified version or mode |
| --- | --- |
| Python | 3.11 and 3.12 supported; both exercised in CI |
| uv | 0.12.1 lockfile installer |
| DataHub Core | v1.6.0 local Quickstart |
| DataHub MCP Server | `mcp-server-datahub@0.6.0` |
| dbt Core | 1.12.0 |
| dbt adapter | `dbt-duckdb==1.10.1` |
| Apache Airflow | 3.3.0 official Linux container |
| Airflow image | `apache/airflow:3.3.0-python3.12` |
| Warehouse validator | isolated DuckDB database |

The release manifest records the final commit and platform matrix. `uv.lock`
is authoritative for the Python environment; both CI and the commands below
install it without re-resolution.

## Deterministic fixture reproduction

```bash
uv sync --all-extras --locked --python 3.12
uv run --no-sync pytest -q
uv run --no-sync ruff check .
uv run --no-sync mypy src scripts
uv run --no-sync evidencegraph demo --output outputs/reproduction
uv run --no-sync evidencegraph ablation
```

The flagship fixture should report:

| Measurement | Expected result |
| --- | ---: |
| Declared affected assets | 7 |
| Repository-only assets found | 3 |
| DataHub-context assets found | 7 |
| Repository-only recall | 42.9% |
| DataHub-context recall | 100.0% |
| Recall improvement | 57.1 percentage points |
| Generated artifacts | 9 |
| Validators passed | 14/14 |
| dbt tests passed | 7/7 |

Repeated fixture runs may have different non-semantic timestamps and output
directories. Asset sets, risk ordering, artifact contents, artifact hashes, and
safety decisions are expected to remain semantically identical.

## Native validator boundary

The fourteen gates include artifact/evidence integrity, eight structured-file parsers, native
unified-diff application, DuckDB execution and parity, dbt build, Airflow DagBag import plus an
executed dependency gate, and ML feature-contract parity.

The verified dbt receipt records dbt Core 1.12.0, exit code 0, and 7 of 7 passed
schema and data tests. The verified Airflow receipt records the official 3.3.0
Linux container, exit code 0, successful DAG import, and enforcement of the
validation-before-publication dependency.

No skipped or unavailable required validator is counted as a pass.

## Live DataHub reproduction

After starting a disposable DataHub Core v1.6.0 Quickstart:

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

The MCP verification report contains payload hashes and observed URNs rather
than credentials or raw server logs. The live run stores a normalized context
snapshot, observations, evidence claims, impacts, artifacts, validations, and a
safety decision.

## Evidence verification

For the final public package, compare every submission number against
`docs/CLAIMS.md` and `submission/manifest.json`. The repository, public demo,
video, and Devpost description must all identify the same release commit.

The following release checks are intentionally pending until publication:

- signed-out checks for every public URL;
- clean-clone verification against the final release commit;
- public release artifact checksums; and
- replacement of all `<PUBLIC_...>` placeholders.
