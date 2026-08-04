"""Bounded EvidenceGraph agent loop."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from evidencegraph.artifacts import ArtifactGenerationError, ArtifactGenerator
from evidencegraph.engine import ImpactEngine
from evidencegraph.models import (
    ChangeKind,
    ChangeRequest,
    ContextSnapshot,
    EvidenceLedger,
    GeneratedArtifact,
)
from evidencegraph.planner import build_claims, build_migration_plan
from evidencegraph.policy import SafetyPolicy
from evidencegraph.validator import BundleValidator
from evidencegraph.writeback import build_writeback_proposals


@dataclass(frozen=True)
class RunPaths:
    root: Path
    ledger_json: Path
    summary_markdown: Path


class EvidenceGraphAgent:
    """Read context, derive impact, generate artifacts, validate, and fail closed."""

    def __init__(self, warehouse_setup: Path) -> None:
        self.impact_engine = ImpactEngine()
        self.generator = ArtifactGenerator()
        self.validator = BundleValidator(warehouse_setup)
        self.policy = SafetyPolicy()

    def run(
        self,
        change: ChangeRequest,
        snapshot: ContextSnapshot,
        *,
        output_root: Path,
        apply_requested: bool = False,
        mutation_tools_available: bool = False,
    ) -> tuple[EvidenceLedger, RunPaths]:
        snapshot_for_hash = snapshot.model_dump(mode="json")
        for observation in snapshot_for_hash["observations"]:
            observation.pop("observed_at", None)
        input_payload = json.dumps(
            {
                "change": change.model_dump(mode="json"),
                "snapshot": snapshot_for_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        input_sha256 = hashlib.sha256(input_payload.encode("utf-8")).hexdigest()
        run_id = f"EG-{input_sha256[:12].upper()}"
        impacts = self.impact_engine.analyze(change, snapshot)
        claims = build_claims(change, snapshot, impacts)
        plan = build_migration_plan(change, impacts, claims)
        generation_error = self._preflight(change, snapshot)
        artifacts: tuple[GeneratedArtifact, ...] = ()
        if generation_error is None:
            try:
                artifacts = self.generator.generate(change, snapshot, impacts, claims, plan)
            except ArtifactGenerationError as exc:
                generation_error = str(exc)
        validations = self.validator.validate(artifacts) if artifacts else ()
        writes_enabled = os.getenv("EVIDENCEGRAPH_ENABLE_WRITES", "").lower() == "true"
        decision, unresolved_risks = self.policy.decide(
            snapshot,
            impacts,
            claims,
            validations,
            apply_requested=apply_requested,
            writes_enabled=writes_enabled,
            mutation_tools_available=mutation_tools_available,
            generation_error=generation_error,
        )
        proposals = (
            build_writeback_proposals(run_id, change, impacts, claims, validations)
            if decision.may_propose_writeback
            else ()
        )
        ledger = EvidenceLedger(
            run_id=run_id,
            change=change,
            snapshot_id=snapshot.snapshot_id,
            input_sha256=input_sha256,
            observations=snapshot.observations,
            claims=claims,
            impacts=impacts,
            migration_plan=plan,
            artifacts=artifacts,
            validations=validations,
            unresolved_risks=unresolved_risks,
            safety_decision=decision,
            writeback_proposals=proposals,
        )
        paths = self._write_run(output_root, ledger)
        return ledger, paths

    def persist(self, output_root: Path, ledger: EvidenceLedger) -> RunPaths:
        """Persist an updated ledger using the same path-containment checks."""

        return self._write_run(output_root, ledger)

    @staticmethod
    def _preflight(change: ChangeRequest, snapshot: ContextSnapshot) -> str | None:
        column_changes = {
            ChangeKind.DROP_COLUMN,
            ChangeKind.RENAME_COLUMN,
            ChangeKind.CHANGE_TYPE,
        }
        if change.kind not in column_changes or change.field is None:
            return None
        source = snapshot.asset_map().get(change.asset_urn)
        if source is None:
            return "The changed asset is absent from the collected DataHub context."
        if change.field not in {field.name for field in source.schema_fields}:
            return (
                f"Changed field {change.field!r} is absent from the observed source schema; "
                "exact migration generation is unsafe."
            )
        has_direct_column_lineage = any(
            edge.upstream_urn == change.asset_urn
            and any(mapping.upstream_field == change.field for mapping in edge.field_mappings)
            for edge in snapshot.lineage
        )
        if not has_direct_column_lineage:
            return (
                f"No observed column lineage maps {change.field!r} from the changed asset; "
                "dataset-level lineage is insufficient for an exact migration."
            )
        return None

    @staticmethod
    def _write_run(output_root: Path, ledger: EvidenceLedger) -> RunPaths:
        run_root = (output_root / ledger.run_id).resolve()
        output_root_resolved = output_root.resolve()
        if output_root_resolved not in run_root.parents:
            raise ValueError("Run path escaped the configured output directory")
        run_root.mkdir(parents=True, exist_ok=True)
        for artifact in ledger.artifacts:
            artifact_path = (run_root / artifact.relative_path).resolve()
            if run_root not in artifact_path.parents:
                raise ValueError(
                    f"Artifact path escaped the run directory: {artifact.relative_path}"
                )
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(artifact.content, encoding="utf-8", newline="\n")
        ledger_json = run_root / "evidence-ledger.json"
        ledger_json.write_text(
            ledger.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        summary_markdown = run_root / "SUMMARY.md"
        summary_markdown.write_text(_render_summary(ledger), encoding="utf-8", newline="\n")
        return RunPaths(run_root, ledger_json, summary_markdown)


def load_change(path: Path) -> ChangeRequest:
    return ChangeRequest.model_validate_json(path.read_text(encoding="utf-8"))


def load_snapshot(path: Path) -> ContextSnapshot:
    return ContextSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def _render_summary(ledger: EvidenceLedger) -> str:
    passed = sum(result.status.value == "passed" for result in ledger.validations)
    failed = sum(result.status.value == "failed" for result in ledger.validations)
    lines = [
        f"# EvidenceGraph run {ledger.run_id}",
        "",
        f"- Change: `{ledger.change.change_id}`",
        f"- Downstream assets: **{len(ledger.impacts)}**",
        f"- Evidence claims: **{len(ledger.claims)}**",
        f"- Generated artifacts: **{len(ledger.artifacts)}**",
        f"- Validations: **{passed} passed / {failed} failed**",
        f"- Write-back executable: **{ledger.safety_decision.may_execute_writeback}**",
        "",
        "## Highest-risk consumers",
        "",
    ]
    lines.extend(
        f"- `{impact.asset_urn}` — {impact.risk_level.value} ({impact.risk_score})"
        for impact in ledger.impacts[:5]
    )
    lines.extend(["", "## Safety decision", ""])
    lines.extend(f"- {reason}" for reason in ledger.safety_decision.reasons)
    lines.append("")
    return "\n".join(lines)
