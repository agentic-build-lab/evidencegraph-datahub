from pathlib import Path

from evidencegraph.models import ChangeRequest, Completeness, ContextSnapshot
from evidencegraph.orchestrator import EvidenceGraphAgent

ROOT = Path(__file__).resolve().parents[1]


def test_incomplete_lineage_blocks_writeback_proposals(
    tmp_path: Path, change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    incomplete = snapshot.model_copy(
        update={
            "completeness": Completeness(
                requested_direction="downstream",
                requested_depth=3,
                pages_exhausted=False,
                frontier_exhausted=False,
                truncated=True,
                notes=("MCP lineage page limit reached.",),
            )
        }
    )
    agent = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql")

    ledger, _ = agent.run(change, incomplete, output_root=tmp_path)

    assert ledger.safety_decision.may_generate is True
    assert ledger.safety_decision.may_propose_writeback is False
    assert ledger.writeback_proposals == ()
    assert "MCP lineage page limit reached." in ledger.unresolved_risks


def test_missing_approved_mapping_refuses_generation(
    tmp_path: Path, change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    no_documents = snapshot.model_copy(update={"documents": ()})
    agent = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql")

    ledger, _ = agent.run(change, no_documents, output_root=tmp_path)

    assert ledger.artifacts == ()
    assert ledger.validations == ()
    assert ledger.safety_decision.may_generate is False
    assert ledger.safety_decision.may_propose_writeback is False
    assert any("replacement mapping" in risk for risk in ledger.unresolved_risks)


def test_missing_column_lineage_blocks_exact_artifact_generation(
    tmp_path: Path, change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    dataset_only = snapshot.model_copy(
        update={
            "lineage": tuple(
                edge.model_copy(update={"field_mappings": ()}) for edge in snapshot.lineage
            )
        }
    )
    agent = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql")

    ledger, _ = agent.run(change, dataset_only, output_root=tmp_path)

    assert len(ledger.impacts) == 7
    assert ledger.artifacts == ()
    assert ledger.safety_decision.may_generate is False
    assert ledger.safety_decision.may_propose_writeback is False
    assert any("column lineage" in risk for risk in ledger.unresolved_risks)


def test_field_absent_from_source_schema_blocks_generation(
    tmp_path: Path, change: ChangeRequest, snapshot: ContextSnapshot
) -> None:
    assets = tuple(
        asset.model_copy(
            update={
                "schema_fields": tuple(
                    field for field in asset.schema_fields if field.name != change.field
                )
            }
        )
        if asset.urn == change.asset_urn
        else asset
        for asset in snapshot.assets
    )
    missing_field = snapshot.model_copy(update={"assets": assets})
    agent = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql")

    ledger, _ = agent.run(change, missing_field, output_root=tmp_path)

    assert ledger.artifacts == ()
    assert ledger.safety_decision.may_generate is False
    assert any("absent from the observed source schema" in risk for risk in ledger.unresolved_risks)
