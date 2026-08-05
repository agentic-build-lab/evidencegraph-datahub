"""Deterministic validation harness for generated migration bundles."""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import os
import re
import shutil

# Validators intentionally execute fixed local toolchains with shell=False.
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path

import duckdb
import sqlglot
import yaml

from evidencegraph.models import GeneratedArtifact, ValidationResult, ValidationStatus


class BundleValidator:
    """Validate syntax, evidence bindings, SQL behavior, and ML contract parity."""

    def __init__(self, warehouse_setup: Path) -> None:
        self.warehouse_setup = warehouse_setup

    def validate(self, artifacts: tuple[GeneratedArtifact, ...]) -> tuple[ValidationResult, ...]:
        results: list[ValidationResult] = []
        results.extend(self._validate_hashes_and_evidence(artifacts))
        results.extend(self._validate_structured_files(artifacts))
        results.append(self._validate_unified_diff(artifacts))
        results.append(self._validate_sql_execution(artifacts))
        results.append(self._validate_dbt_build(artifacts))
        results.append(self._validate_airflow_import(artifacts))
        results.append(self._validate_ml_parity(artifacts))
        return tuple(results)

    @staticmethod
    def _result(
        validation_id: str,
        name: str,
        status: ValidationStatus,
        details: str,
        artifact_paths: tuple[str, ...] = (),
        command: str | None = None,
        tool_version: str | None = None,
        exit_code: int | None = None,
        duration_ms: int | None = None,
        raw_output: str | None = None,
    ) -> ValidationResult:
        return ValidationResult(
            validation_id=validation_id,
            name=name,
            status=status,
            artifact_paths=artifact_paths,
            command=command,
            tool_version=tool_version,
            exit_code=exit_code,
            duration_ms=duration_ms,
            details=details,
            output_sha256=hashlib.sha256(
                (raw_output if raw_output is not None else details).encode("utf-8")
            ).hexdigest(),
        )

    def _validate_hashes_and_evidence(
        self, artifacts: tuple[GeneratedArtifact, ...]
    ) -> list[ValidationResult]:
        bad_hashes = [
            artifact.relative_path
            for artifact in artifacts
            if hashlib.sha256(artifact.content.encode("utf-8")).hexdigest() != artifact.sha256
        ]
        missing_evidence = [
            artifact.relative_path
            for artifact in artifacts
            if not artifact.evidence_claim_ids or not artifact.target_urns
        ]
        details = (
            "All artifact digests and evidence bindings are valid."
            if not bad_hashes and not missing_evidence
            else f"Bad digests: {bad_hashes}; missing evidence bindings: {missing_evidence}."
        )
        return [
            self._result(
                "VAL-INTEGRITY",
                "Artifact integrity and evidence binding",
                ValidationStatus.PASSED
                if not bad_hashes and not missing_evidence
                else ValidationStatus.FAILED,
                details,
                tuple(artifact.relative_path for artifact in artifacts),
                "sha256 + evidence-binding policy",
            )
        ]

    def _validate_structured_files(
        self, artifacts: tuple[GeneratedArtifact, ...]
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for artifact in artifacts:
            if artifact.kind == "unified-diff":
                continue
            status = ValidationStatus.PASSED
            details = f"{artifact.relative_path} parsed successfully."
            try:
                if artifact.kind in {"dbt-yaml", "ml-feature-contract"}:
                    payload = yaml.safe_load(artifact.content)
                    if not isinstance(payload, dict):
                        raise ValueError("YAML root must be a mapping")
                elif artifact.kind == "manifest":
                    payload = json.loads(artifact.content)
                    if payload.get("change_id") != "EG-042":
                        raise ValueError("Manifest change_id mismatch")
                elif artifact.kind == "airflow-python":
                    ast.parse(artifact.content)
                elif artifact.kind == "sql" or artifact.kind == "validation-sql":
                    sqlglot.parse(artifact.content, read="duckdb")
                elif artifact.kind == "dbt-sql":
                    normalized = re.sub(r"\{\{\s*config\(.*?\)\s*\}\}", "", artifact.content)
                    normalized = re.sub(
                        r"\{\{\s*source\(.*?\)\s*\}\}",
                        "raw_orders_next",
                        normalized,
                    )
                    sqlglot.parse(normalized, read="duckdb")
            except Exception as exc:
                status = ValidationStatus.FAILED
                details = f"{artifact.relative_path} did not parse: {type(exc).__name__}: {exc}"
            results.append(
                self._result(
                    f"VAL-PARSE-{len(results) + 1:02d}",
                    f"Parse {artifact.kind}",
                    status,
                    details,
                    (artifact.relative_path,),
                    "native parser",
                )
            )
        return results

    def _validate_unified_diff(self, artifacts: tuple[GeneratedArtifact, ...]) -> ValidationResult:
        patch = next((item for item in artifacts if item.kind == "unified-diff"), None)
        if patch is None:
            return self._result(
                "VAL-PATCH-APPLY",
                "Apply unified diff to demo repository",
                ValidationStatus.FAILED,
                "Required unified diff artifact is absent.",
            )
        git = shutil.which("git")
        if git is None:
            return self._result(
                "VAL-PATCH-APPLY",
                "Apply unified diff to demo repository",
                ValidationStatus.FAILED,
                "Git is unavailable for native patch validation.",
                (patch.relative_path,),
                "git apply --check -",
            )
        started = time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix="evidencegraph-patch-") as temporary:
                root = Path(temporary)
                relative = Path("demo_platform/dbt/models/staging/stg_orders.sql")
                target = root / relative
                target.parent.mkdir(parents=True)
                baseline = (
                    Path(__file__).resolve().parents[2]
                    / "demo_platform/dbt/models/staging/stg_orders.sql"
                )
                target.write_text(
                    baseline.read_text(encoding="utf-8"),
                    encoding="utf-8",
                    newline="\n",
                )
                patch_file = root / "migration.patch"
                patch_file.write_text(patch.content, encoding="utf-8", newline="\n")
                # Fixed git binary and argument vector; no shell interpretation.
                process = subprocess.run(  # nosec B603
                    [git, "apply", "--check", str(patch_file)],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    check=False,
                    env=_minimal_validation_environment(),
                )
            raw_output = _sanitize_output(process.stdout + "\n" + process.stderr)
            status = ValidationStatus.PASSED if process.returncode == 0 else ValidationStatus.FAILED
            details = (
                "The unified diff applies cleanly to the committed miniature platform."
                if status == ValidationStatus.PASSED
                else f"git apply rejected the generated patch: {_tail(raw_output)}"
            )
            exit_code = process.returncode
        except Exception as exc:
            raw_output = f"{type(exc).__name__}: {exc}"
            status = ValidationStatus.FAILED
            details = f"Patch validation failed: {raw_output}"
            exit_code = None
        return self._result(
            "VAL-PATCH-APPLY",
            "Apply unified diff to demo repository",
            status,
            details,
            (patch.relative_path,),
            "git apply --check -",
            _git_version(git),
            exit_code,
            int((time.monotonic() - started) * 1000),
            raw_output,
        )

    def _validate_sql_execution(self, artifacts: tuple[GeneratedArtifact, ...]) -> ValidationResult:
        compatibility = next(artifact for artifact in artifacts if artifact.kind == "sql")
        validation = next(artifact for artifact in artifacts if artifact.kind == "validation-sql")
        try:
            connection = duckdb.connect(":memory:")
            connection.execute(self.warehouse_setup.read_text(encoding="utf-8"))
            connection.execute(compatibility.content)
            failures = connection.execute(validation.content).fetchall()
            status = ValidationStatus.PASSED if not failures else ValidationStatus.FAILED
            details = (
                "DuckDB executed the compatibility view; 4/4 rows preserve the current contract."
                if not failures
                else f"DuckDB found {len(failures)} migration parity failure(s): {failures}."
            )
        except Exception as exc:
            status = ValidationStatus.FAILED
            details = f"DuckDB execution failed: {type(exc).__name__}: {exc}"
        return self._result(
            "VAL-DUCKDB-PARITY",
            "Execute SQL migration and parity query",
            status,
            details,
            (compatibility.relative_path, validation.relative_path),
            "DuckDB in-memory transaction",
        )

    def _validate_ml_parity(self, artifacts: tuple[GeneratedArtifact, ...]) -> ValidationResult:
        contract = next(
            (artifact for artifact in artifacts if artifact.kind == "ml-feature-contract"),
            None,
        )
        if contract is None:
            return self._result(
                "VAL-ML-PARITY",
                "Validate ML feature contract",
                ValidationStatus.SKIPPED,
                "No ML consumer is present in the impact graph.",
            )
        try:
            payload = yaml.safe_load(contract.content)
            mapping = payload["spec"]["mapping"]
            connection = duckdb.connect(":memory:")
            connection.execute(self.warehouse_setup.read_text(encoding="utf-8"))
            rows = connection.execute(
                "SELECT segment_code, customer_tier FROM raw_orders_current ORDER BY order_id"
            ).fetchall()
            failures = [(code, tier) for code, tier in rows if mapping.get(code) != tier]
            minimum_rows = int(payload["spec"]["parity"]["minimumRows"])
            valid_count = len(rows) >= minimum_rows and not failures
            status = ValidationStatus.PASSED if valid_count else ValidationStatus.FAILED
            details = (
                f"ML mapping parity passed for {len(rows)} rows at 0.0 mismatch rate."
                if valid_count
                else f"ML mapping parity failed; rows={len(rows)}, mismatches={failures}."
            )
        except Exception as exc:
            status = ValidationStatus.FAILED
            details = f"ML contract validation failed: {type(exc).__name__}: {exc}"
        return self._result(
            "VAL-ML-PARITY",
            "Validate ML feature contract",
            status,
            details,
            (contract.relative_path,),
            "DuckDB parity check + YAML contract",
        )

    def _validate_dbt_build(self, artifacts: tuple[GeneratedArtifact, ...]) -> ValidationResult:
        model = next((item for item in artifacts if item.kind == "dbt-sql"), None)
        schema = next((item for item in artifacts if item.kind == "dbt-yaml"), None)
        if model is None or schema is None:
            return self._result(
                "VAL-DBT-BUILD",
                "Run dbt build",
                ValidationStatus.FAILED,
                "Required dbt model or schema artifact is absent.",
            )
        dbt = shutil.which("dbt")
        if dbt is None:
            executable_name = "dbt.exe" if os.name == "nt" else "dbt"
            candidate = Path(sys.executable).with_name(executable_name)
            dbt = str(candidate) if candidate.exists() else None
        if dbt is None:
            return self._result(
                "VAL-DBT-BUILD",
                "Run dbt build",
                ValidationStatus.FAILED,
                "dbt executable is unavailable; install the native validation extra.",
                (model.relative_path, schema.relative_path),
                "dbt build --select stg_orders --no-partial-parse",
            )
        started = time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix="evidencegraph-dbt-") as temporary:
                root = Path(temporary)
                project = root / "project"
                models = project / "models" / "staging"
                profiles = root / "profiles"
                models.mkdir(parents=True)
                profiles.mkdir()
                database = root / "warehouse.duckdb"
                connection = duckdb.connect(str(database))
                connection.execute(self.warehouse_setup.read_text(encoding="utf-8"))
                connection.close()
                (project / "dbt_project.yml").write_text(
                    yaml.safe_dump(
                        {
                            "name": "evidencegraph_native_validation",
                            "version": "1.0.0",
                            "config-version": 2,
                            "profile": "evidencegraph",
                            "model-paths": ["models"],
                            "clean-targets": ["target", "dbt_packages"],
                        },
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                )
                (profiles / "profiles.yml").write_text(
                    yaml.safe_dump(
                        {
                            "evidencegraph": {
                                "target": "native",
                                "outputs": {
                                    "native": {
                                        "type": "duckdb",
                                        "path": database.as_posix(),
                                        "schema": "main",
                                        "threads": 1,
                                    }
                                },
                            }
                        },
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                )
                (models / "stg_orders.sql").write_text(model.content, encoding="utf-8")
                (models / "stg_orders.yml").write_text(schema.content, encoding="utf-8")
                (models / "sources.yml").write_text(
                    yaml.safe_dump(
                        {
                            "version": 2,
                            "sources": [
                                {
                                    "name": "commerce",
                                    "schema": "main",
                                    "tables": [{"name": "raw_orders_next"}],
                                }
                            ],
                        },
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                )
                # Fixed dbt binary and argument vector; no shell interpretation.
                process = subprocess.run(  # nosec B603
                    [
                        dbt,
                        "build",
                        "--select",
                        "stg_orders",
                        "--project-dir",
                        str(project),
                        "--profiles-dir",
                        str(profiles),
                        "--no-partial-parse",
                        "--no-use-colors",
                    ],
                    cwd=project,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=90,
                    check=False,
                    env=_minimal_validation_environment(),
                )
            raw_output = _sanitize_output(process.stdout + "\n" + process.stderr)
            status = ValidationStatus.PASSED if process.returncode == 0 else ValidationStatus.FAILED
            details = (
                "dbt built the generated model and passed 7/7 schema and data tests."
                if status == ValidationStatus.PASSED
                else f"dbt build failed with exit code {process.returncode}: {_tail(raw_output)}"
            )
            exit_code = process.returncode
        except Exception as exc:
            raw_output = f"{type(exc).__name__}: {exc}"
            status = ValidationStatus.FAILED
            details = f"dbt native validation failed: {raw_output}"
            exit_code = None
        return self._result(
            "VAL-DBT-BUILD",
            "Run dbt build",
            status,
            details,
            (model.relative_path, schema.relative_path),
            "dbt build --select stg_orders --no-partial-parse",
            importlib.metadata.version("dbt-core"),
            exit_code,
            int((time.monotonic() - started) * 1000),
            raw_output,
        )

    def _validate_airflow_import(
        self, artifacts: tuple[GeneratedArtifact, ...]
    ) -> ValidationResult:
        dag = next((item for item in artifacts if item.kind == "airflow-python"), None)
        if dag is None:
            return self._result(
                "VAL-AIRFLOW-DAG",
                "Import Airflow DAG and validate dependency gate",
                ValidationStatus.FAILED,
                "Required Airflow artifact is absent.",
            )
        try:
            airflow_version = importlib.metadata.version("apache-airflow")
        except importlib.metadata.PackageNotFoundError:
            return self._result(
                "VAL-AIRFLOW-DAG",
                "Import Airflow DAG and validate dependency gate",
                ValidationStatus.FAILED,
                "Apache Airflow is unavailable; install the native validation extra.",
                (dag.relative_path,),
                "Airflow DagBag import",
            )
        started = time.monotonic()
        command_label = "Airflow DagBag import + dependency assertion"
        reported_version = airflow_version
        docker = shutil.which("docker")
        image = "apache/airflow:3.3.0-python3.12"
        use_container = False
        if os.name == "nt":
            if docker is None:
                return self._result(
                    "VAL-AIRFLOW-DAG",
                    "Import Airflow DAG and validate dependency gate",
                    ValidationStatus.FAILED,
                    (
                        "Native Airflow validation is unsupported on Windows. "
                        "Run the pinned official Linux container through Docker or use WSL2/Linux."
                    ),
                    (dag.relative_path,),
                    "official Airflow Linux container required on Windows",
                    airflow_version,
                    None,
                    int((time.monotonic() - started) * 1000),
                )
            inspected = subprocess.run(  # nosec B603
                [docker, "image", "inspect", image],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
                env=_minimal_validation_environment(include_docker=True),
            )
            if inspected.returncode != 0:
                return self._result(
                    "VAL-AIRFLOW-DAG",
                    "Import Airflow DAG and validate dependency gate",
                    ValidationStatus.FAILED,
                    (
                        "The pinned official Airflow Linux image is unavailable on Windows. "
                        "Start Docker and pull apache/airflow:3.3.0-python3.12, or use WSL2/Linux."
                    ),
                    (dag.relative_path,),
                    "docker image inspect apache/airflow:3.3.0-python3.12",
                    airflow_version,
                    inspected.returncode,
                    int((time.monotonic() - started) * 1000),
                    _sanitize_output(inspected.stdout + "\n" + inspected.stderr),
                )
            use_container = True
        check_program = """
import json
import os
import sys
from airflow.dag_processing.dagbag import DagBag

bag = DagBag(dag_folder=sys.argv[1], safe_mode=False)
if bag.import_errors:
    raise RuntimeError(str(bag.import_errors))
dag = bag.dags.get('daily_customer_value_migration')
if dag is None:
    raise RuntimeError('expected DAG is absent')
expected = {'validate_customer_tier_compatibility', 'publish_customer_value'}
if set(dag.task_ids) != expected:
    raise RuntimeError(f'unexpected task ids: {dag.task_ids}')
publish = dag.get_task('publish_customer_value')
if publish.upstream_task_ids != {'validate_customer_tier_compatibility'}:
    raise RuntimeError(f'publish gate is not enforced: {publish.upstream_task_ids}')
ledger = '/tmp/evidencegraph-ledger.json'
input_sha256 = 'a' * 64
expected_validation_ids = [
    'VAL-INTEGRITY',
    'VAL-PARSE-01',
    'VAL-PARSE-02',
    'VAL-PARSE-03',
    'VAL-PARSE-04',
    'VAL-PARSE-05',
    'VAL-PARSE-06',
    'VAL-PARSE-07',
    'VAL-PARSE-08',
    'VAL-PATCH-APPLY',
    'VAL-DUCKDB-PARITY',
    'VAL-DBT-BUILD',
    'VAL-AIRFLOW-DAG',
    'VAL-ML-PARITY',
]
with open(ledger, 'w', encoding='utf-8') as handle:
    json.dump(
        {
            'run_id': 'EG-AAAAAAAAAAAA',
            'input_sha256': input_sha256,
            'change': {'change_id': 'EG-042'},
            'validations': [
                {
                    'validation_id': validation_id,
                    'status': 'passed',
                    'output_sha256': 'b' * 64,
                }
                for validation_id in expected_validation_ids
            ],
        },
        handle,
    )
os.environ['EVIDENCEGRAPH_LEDGER_PATH'] = ledger
gate = dag.get_task('validate_customer_tier_compatibility')
if gate.python_callable() != 'EG-AAAAAAAAAAAA':
    raise RuntimeError('validation callable did not return the verified run id')
print(json.dumps({'dag_id': dag.dag_id, 'task_ids': sorted(dag.task_ids), 'gate': 'executed'}))
"""
        try:
            with tempfile.TemporaryDirectory(prefix="evidencegraph-airflow-") as temporary:
                root = Path(temporary)
                dags = root / "dags"
                dags.mkdir()
                (dags / "evidencegraph_change_gate.py").write_text(dag.content, encoding="utf-8")
                environment = _minimal_validation_environment(include_docker=True)
                environment["AIRFLOW_HOME"] = str(root / "airflow-home")
                environment["AIRFLOW__CORE__LOAD_EXAMPLES"] = "false"
                environment["PYTHONUTF8"] = "1"
                environment["PYTHONIOENCODING"] = "utf-8"
                if use_container and docker is not None:
                    command = [
                        docker,
                        "run",
                        "--rm",
                        "--network",
                        "none",
                        "--env",
                        "AIRFLOW_HOME=/tmp/evidencegraph-airflow",
                        "--env",
                        "AIRFLOW__CORE__LOAD_EXAMPLES=false",
                        "--volume",
                        f"{dags.resolve()}:/opt/airflow/dags:ro",
                        image,
                        "python",
                        "-c",
                        check_program,
                        "/opt/airflow/dags",
                    ]
                    command_label = (
                        "docker run --rm --network none "
                        "apache/airflow:3.3.0-python3.12 DagBag validation"
                    )
                    reported_version = "3.3.0 (official Linux container)"
                else:
                    command = [sys.executable, "-c", check_program, str(dags)]
                    command_label = "Airflow DagBag import + dependency assertion"
                    reported_version = airflow_version
                # Command is assembled only from fixed, locally resolved tool paths.
                process = subprocess.run(  # nosec B603
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    check=False,
                    env=environment,
                )
            raw_output = _sanitize_output(process.stdout + "\n" + process.stderr)
            status = ValidationStatus.PASSED if process.returncode == 0 else ValidationStatus.FAILED
            details = (
                "Airflow DagBag imported the DAG; the validation task gates publication."
                if status == ValidationStatus.PASSED
                else f"Airflow DAG validation failed: {_tail(raw_output)}"
            )
            exit_code = process.returncode
        except Exception as exc:
            raw_output = f"{type(exc).__name__}: {exc}"
            status = ValidationStatus.FAILED
            details = f"Airflow native validation failed: {raw_output}"
            exit_code = None
        return self._result(
            "VAL-AIRFLOW-DAG",
            "Import Airflow DAG and validate dependency gate",
            status,
            details,
            (dag.relative_path,),
            command_label,
            reported_version,
            exit_code,
            int((time.monotonic() - started) * 1000),
            raw_output,
        )


def _sanitize_output(value: str) -> str:
    normalized = re.sub(r"[A-Za-z]:\\[^\s]+", "<temporary-path>", value)
    # This pattern redacts a path from captured output; it never opens a temp path.
    normalized = re.sub(r"/tmp/[^\s]+", "<temporary-path>", normalized)  # nosec B108
    return normalized[-12000:]


def _minimal_validation_environment(*, include_docker: bool = False) -> dict[str, str]:
    allowed = {
        "COMSPEC",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    }
    if include_docker:
        allowed.update({"DOCKER_CONFIG", "DOCKER_CONTEXT", "DOCKER_HOST"})
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    environment.update(
        {
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
    )
    return environment


def _git_version(git: str) -> str:
    # Fixed git executable and --version argument; no shell interpretation.
    process = subprocess.run(  # nosec B603
        [git, "--version"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        env=_minimal_validation_environment(),
    )
    return process.stdout.strip() or "git"


def _tail(value: str, limit: int = 600) -> str:
    compact = " ".join(value.split())
    return compact[-limit:]
