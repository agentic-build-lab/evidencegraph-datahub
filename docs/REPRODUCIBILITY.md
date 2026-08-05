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

Native Airflow execution is unsupported on Windows. On Windows, the validation
harness requires Docker with the pinned
`apache/airflow:3.3.0-python3.12` image; otherwise `VAL-AIRFLOW-DAG` fails
closed with an explicit platform error. WSL2 or Linux can use the native
environment installed from `uv.lock`.

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

On Linux, WSL2, or Windows with the pinned Airflow image available, the
flagship fixture should report:

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

Windows without that container intentionally reports `VAL-AIRFLOW-DAG` as
failed, keeps the overall decision fail-closed, and therefore does not satisfy
the 14/14 release-candidate boundary.

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

## Public Assurance Studio reproduction

The hosted demo is a labeled replay over repository-owned evidence. It does not
expose a DataHub credential or mutation endpoint. Rebuild the production page
from a clean clone with the same install constraints used by CI:

```bash
cd site
npm ci --ignore-scripts --no-fund
npm audit --audit-level=high
npm run lint
npm test
```

The rendered-page tests require the 3-of-7 repository baseline, the 7-of-7
DataHub result, the complete-versus-missing-lineage authority switch, nine
artifacts, fourteen recorded gates, and inspectable public evidence links.

## Launch-film source reproduction

Narration, phrase timings, compositions, and the video build scripts are
versioned. The DOVA-SYNDROME music file is intentionally not redistributed.
Download Track 1 of “A Little Story” from the official page linked in
`videos/evidencegraph-launch/MUSIC_CREDITS.md`, then run:

```powershell
cd videos/evidencegraph-launch
npm ci
Get-FileHash assets/A_Little_Story_Kei_Morimoto.mp3 -Algorithm SHA256
powershell -ExecutionPolicy Bypass -File .hyperframes/prepare-bgm.ps1
node .hyperframes/build-phrase-captions.mjs .
npm run check
```

The source track used for the release has SHA-256
`dff5eeb1f30499692e43022aebb02fe091805571f05b4820fc02e19032c3873e`.
The 130-second, 256 kbps render edit has SHA-256
`a3ab90400ae39b79730997de0b2e1edca2ca38f9a96a3076cfb9975e25279ff0`
in the verified release environment. The committed caption build produces 31
non-overlapping phrase groups of 5-16 words; the HyperFrames check gates
runtime, layout, motion, and WCAG contrast before final preview approval.

## Evidence verification

For the final public package, compare every submission number against
`docs/CLAIMS.md` and `submission/manifest.json`. The repository, public demo,
video, and Devpost description must all identify the same release commit.

The publication gates for the current release candidate are recorded in
`submission/manifest.json`. Every gate must be `true` before submission:
signed-out checks for the repository, demo, video, sample outputs, release, and
Devpost page; clean-clone verification; release-asset checksums; secret and
personal-data scanning; and replacement of every submission placeholder.
Recalculate attachment hashes after downloading them from the public release
rather than trusting filenames alone.
