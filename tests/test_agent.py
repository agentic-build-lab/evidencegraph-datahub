import os
import shutil
import subprocess
from pathlib import Path

import pytest

from evidencegraph.models import ChangeRequest, ContextSnapshot, ValidationStatus
from evidencegraph.orchestrator import EvidenceGraphAgent

ROOT = Path(__file__).resolve().parents[1]
AIRFLOW_IMAGE = "apache/airflow:3.3.0-python3.12"


def _native_airflow_validation_available() -> bool:
    if os.name != "nt":
        return True
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        inspected = subprocess.run(
            [docker, "image", "inspect", AIRFLOW_IMAGE],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return inspected.returncode == 0


@pytest.mark.skipif(
    not _native_airflow_validation_available(),
    reason="Windows requires the pinned official Airflow Linux image for native DAG validation.",
)
def test_flagship_run_generates_validated_evidence_bundle(
    tmp_path: Path, change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    agent = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql")

    ledger, paths = agent.run(change, snapshot, output_root=tmp_path)

    assert len(ledger.impacts) == 7
    assert len(ledger.artifacts) == 9
    assert len(ledger.validations) == 14
    assert all(result.status == ValidationStatus.PASSED for result in ledger.validations)
    assert ledger.safety_decision.may_propose_writeback is True
    assert ledger.safety_decision.may_execute_writeback is False
    assert {proposal.tool for proposal in ledger.writeback_proposals} == {
        "add_tags",
        "update_description",
        "save_document",
    }
    assert paths.ledger_json.exists()
    assert paths.summary_markdown.exists()
    assert (paths.root / "migration/dbt/models/staging/stg_orders.sql").exists()
    assert (paths.root / "migration/patches/demo-platform.patch").exists()


def test_deterministic_run_is_idempotent(
    tmp_path: Path, change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    agent = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql")

    first, first_paths = agent.run(change, snapshot, output_root=tmp_path)
    second, second_paths = agent.run(change, snapshot, output_root=tmp_path)

    assert first.run_id == second.run_id
    assert first.input_sha256 == second.input_sha256
    assert first_paths.root == second_paths.root
