"""Typed contracts shared by EvidenceGraph collectors, planners, and validators."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Base model that rejects unexpected data at trust boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AssetKind(StrEnum):
    DATASET = "dataset"
    DATA_JOB = "data_job"
    PIPELINE = "pipeline"
    DASHBOARD = "dashboard"
    CHART = "chart"
    ML_FEATURE = "ml_feature"
    ML_FEATURE_TABLE = "ml_feature_table"
    ML_MODEL = "ml_model"
    ML_MODEL_DEPLOYMENT = "ml_model_deployment"


class Criticality(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(StrEnum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ChangeKind(StrEnum):
    DROP_COLUMN = "drop_column"
    RENAME_COLUMN = "rename_column"
    CHANGE_TYPE = "change_type"
    CHANGE_CONTRACT = "change_contract"
    CHANGE_PIPELINE = "change_pipeline"
    CHANGE_ML_FEATURE = "change_ml_feature"


class ClaimStatus(StrEnum):
    ABSENT = "absent"
    NOT_QUERIED = "not_queried"
    READ_FAILED = "read_failed"
    INCOMPLETE = "incomplete"
    UNSUPPORTED = "unsupported"
    OBSERVED = "observed"
    DERIVED = "derived"
    UNRESOLVED = "unresolved"
    CONTRADICTED = "contradicted"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ClosureStatus(StrEnum):
    CLOSED = "closed"
    REFUSED = "refused"


class SchemaField(StrictModel):
    name: str
    native_type: str
    nullable: bool = True
    description: str | None = None
    tags: tuple[str, ...] = ()


class DataContract(StrictModel):
    contract_urn: str
    required_fields: tuple[str, ...] = ()
    owner_urns: tuple[str, ...] = ()
    status: str = "active"
    rules: dict[str, Any] = Field(default_factory=dict)


class Asset(StrictModel):
    urn: str
    name: str
    kind: AssetKind
    platform: str
    description: str = ""
    owners: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    domain: str | None = None
    criticality: Criticality = Criticality.MEDIUM
    schema_fields: tuple[SchemaField, ...] = ()
    contract: DataContract | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class FieldMapping(StrictModel):
    upstream_field: str
    downstream_field: str


class LineageEdge(StrictModel):
    upstream_urn: str
    downstream_urn: str
    field_mappings: tuple[FieldMapping, ...] = ()
    transformation: str | None = None
    source_observation_id: str


class ContextDocument(StrictModel):
    urn: str
    title: str
    body: str
    related_urns: tuple[str, ...] = ()
    facts: dict[str, Any] = Field(default_factory=dict)
    source_observation_id: str


class Observation(StrictModel):
    observation_id: str
    interface: str
    operation: str
    object_urn: str | None = None
    locator: str
    payload_sha256: str
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class Completeness(StrictModel):
    requested_direction: str = "downstream"
    requested_depth: int = 10
    pages_exhausted: bool = True
    frontier_exhausted: bool = True
    truncated: bool = False
    permission_denials: tuple[str, ...] = ()
    unsupported_entities: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def is_complete(self) -> bool:
        return (
            self.pages_exhausted
            and self.frontier_exhausted
            and not self.truncated
            and not self.permission_denials
            and not self.unsupported_entities
        )


class ContextSnapshot(StrictModel):
    snapshot_id: str
    assets: tuple[Asset, ...]
    lineage: tuple[LineageEdge, ...]
    documents: tuple[ContextDocument, ...] = ()
    observations: tuple[Observation, ...]
    completeness: Completeness

    def asset_map(self) -> dict[str, Asset]:
        return {asset.urn: asset for asset in self.assets}


class ChangeRequest(StrictModel):
    change_id: str
    asset_urn: str
    kind: ChangeKind
    field: str | None = None
    proposed_field: str | None = None
    proposed_type: str | None = None
    requested_by: str
    reason: str
    proposal_revision: str
    before_contract: dict[str, Any]
    after_contract: dict[str, Any]
    repository_ref: str | None = None

    @field_validator("change_id", "asset_urn", "requested_by", "reason", "proposal_revision")
    @classmethod
    def required_strings_are_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must be a non-empty string")
        return value

    @model_validator(mode="after")
    def validate_change_shape(self) -> ChangeRequest:
        column_changes = {
            ChangeKind.DROP_COLUMN,
            ChangeKind.RENAME_COLUMN,
            ChangeKind.CHANGE_TYPE,
        }
        if self.kind in column_changes and not (self.field and self.field.strip()):
            raise ValueError("field is required for column changes")
        if self.kind == ChangeKind.RENAME_COLUMN and not (
            self.proposed_field and self.proposed_field.strip()
        ):
            raise ValueError("proposed_field is required for rename_column")
        if self.kind == ChangeKind.CHANGE_TYPE and not (
            self.proposed_type and self.proposed_type.strip()
        ):
            raise ValueError("proposed_type is required for change_type")
        if not self.asset_urn.startswith("urn:li:"):
            raise ValueError("asset_urn must be a DataHub URN")
        if self.kind == ChangeKind.DROP_COLUMN and self.field is not None:
            before_fields = self.before_contract.get("required_fields")
            after_fields = self.after_contract.get("required_fields")
            if not isinstance(before_fields, list) or self.field not in before_fields:
                raise ValueError("before_contract must include the dropped field")
            if not isinstance(after_fields, list) or self.field in after_fields:
                raise ValueError("after_contract must remove the dropped field")
        return self


class Impact(StrictModel):
    asset_urn: str
    asset_name: str
    kind: AssetKind
    affected_fields: tuple[str, ...]
    paths: tuple[tuple[str, ...], ...]
    owners: tuple[str, ...]
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    rationale: tuple[str, ...]
    source_observation_ids: tuple[str, ...]


class MigrationStep(StrictModel):
    step_id: str
    order: int
    title: str
    action: str
    target_urns: tuple[str, ...]
    owner_urns: tuple[str, ...]
    blocking: bool
    evidence_claim_ids: tuple[str, ...] = ()


class EvidenceClaim(StrictModel):
    claim_id: str
    statement: str
    subject_urn: str | None = None
    predicate: str
    value: Any
    status: ClaimStatus
    confidence: float = Field(ge=0.0, le=1.0)
    source_observation_ids: tuple[str, ...] = ()
    observed_at: datetime | None = None
    derivation: str | None = None
    test_status: ValidationStatus | None = None
    unresolved_risks: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_provenance(self) -> EvidenceClaim:
        if not self.claim_id.strip() or not self.statement.strip() or not self.predicate.strip():
            raise ValueError("claim id, statement, and predicate must be non-empty")
        if self.status == ClaimStatus.OBSERVED and not self.source_observation_ids:
            raise ValueError("observed claims require a source observation")
        if self.status == ClaimStatus.DERIVED and (
            not self.source_observation_ids or not self.derivation
        ):
            raise ValueError("derived claims require observations and a derivation rule")
        return self


class GeneratedArtifact(StrictModel):
    relative_path: str
    kind: str
    purpose: str
    content: str
    sha256: str
    target_urns: tuple[str, ...]
    evidence_claim_ids: tuple[str, ...]


class ValidationResult(StrictModel):
    validation_id: str
    name: str
    status: ValidationStatus
    artifact_paths: tuple[str, ...] = ()
    command: str | None = None
    tool_version: str | None = None
    exit_code: int | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    details: str
    output_sha256: str


class WritebackProposal(StrictModel):
    proposal_id: str
    tool: str
    arguments: dict[str, Any]
    purpose: str
    idempotency_key: str
    requires_human_approval: bool = True


class MutationReceipt(StrictModel):
    proposal_id: str
    tool: str
    status: str
    response_sha256: str
    target_urn: str | None = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SafetyDecision(StrictModel):
    may_generate: bool
    may_propose_writeback: bool
    may_execute_writeback: bool
    reasons: tuple[str, ...]
    required_human_actions: tuple[str, ...] = ()


class EvidenceLedger(StrictModel):
    schema_version: str = "1.0"
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    change: ChangeRequest
    snapshot_id: str
    input_sha256: str
    observations: tuple[Observation, ...]
    claims: tuple[EvidenceClaim, ...]
    impacts: tuple[Impact, ...]
    migration_plan: tuple[MigrationStep, ...]
    artifacts: tuple[GeneratedArtifact, ...]
    validations: tuple[ValidationResult, ...]
    unresolved_risks: tuple[str, ...]
    safety_decision: SafetyDecision
    writeback_proposals: tuple[WritebackProposal, ...] = ()
    mutation_receipts: tuple[MutationReceipt, ...] = ()


class ClosureReceipt(StrictModel):
    change_id: str
    proposal_revision: str
    before_snapshot_id: str
    after_snapshot_id: str
    patch_sha256: str
    applied_at: datetime
    oldest_after_observation_at: datetime | None
    newest_after_observation_at: datetime | None
    remaining_impact_urns: tuple[str, ...]
    validation_ids: tuple[str, ...]
    status: ClosureStatus
    reasons: tuple[str, ...]
