"""Fail-closed policy decisions for EvidenceGraph."""

from __future__ import annotations

from evidencegraph.models import (
    ClaimStatus,
    ContextSnapshot,
    EvidenceClaim,
    Impact,
    RiskLevel,
    SafetyDecision,
    ValidationResult,
    ValidationStatus,
)


class SafetyPolicy:
    """Prevent unsupported claims and mutations from leaving the agent boundary."""

    def decide(
        self,
        snapshot: ContextSnapshot,
        impacts: tuple[Impact, ...],
        claims: tuple[EvidenceClaim, ...],
        validations: tuple[ValidationResult, ...],
        *,
        apply_requested: bool,
        writes_enabled: bool,
        mutation_tools_available: bool,
        generation_error: str | None = None,
    ) -> tuple[SafetyDecision, tuple[str, ...]]:
        reasons: list[str] = []
        unresolved: list[str] = []
        required_actions: list[str] = []

        if generation_error:
            reasons.append(f"Artifact generation is unsupported: {generation_error}")
            unresolved.append(generation_error)
        if not snapshot.completeness.is_complete:
            reasons.append("DataHub lineage completeness invariants are not satisfied.")
            unresolved.extend(snapshot.completeness.notes or ("Lineage frontier is incomplete.",))
        nonpassing_validations = tuple(
            result for result in validations if result.status != ValidationStatus.PASSED
        )
        if nonpassing_validations:
            reasons.append(
                f"{len(nonpassing_validations)} deterministic validation(s) did not pass."
            )
            unresolved.extend(result.details for result in nonpassing_validations)
        acceptable_claim_states = {ClaimStatus.OBSERVED, ClaimStatus.DERIVED, ClaimStatus.ABSENT}
        unresolved_claims = tuple(
            claim for claim in claims if claim.status not in acceptable_claim_states
        )
        if unresolved_claims:
            reasons.append(f"{len(unresolved_claims)} evidence claim(s) remain unresolved.")
            unresolved.extend(claim.statement for claim in unresolved_claims)
        unowned_high_risk = tuple(
            impact
            for impact in impacts
            if impact.risk_level in {RiskLevel.BLOCKER, RiskLevel.CRITICAL, RiskLevel.HIGH}
            and not impact.owners
        )
        if unowned_high_risk:
            reasons.append("A high-risk affected asset has no observed DataHub owner.")
            unresolved.extend(f"Missing owner: {impact.asset_urn}" for impact in unowned_high_risk)

        may_generate = generation_error is None
        safe_evidence = (
            snapshot.completeness.is_complete
            and not nonpassing_validations
            and not unresolved_claims
            and not unowned_high_risk
            and generation_error is None
        )
        may_propose = safe_evidence

        if not apply_requested:
            reasons.append("Live write-back was not requested; this run is read-only.")
        if not writes_enabled:
            reasons.append("EVIDENCEGRAPH_ENABLE_WRITES is not true.")
        if not mutation_tools_available:
            reasons.append("Required DataHub MCP mutation tools were not discovered.")
        may_execute = (
            may_propose and apply_requested and writes_enabled and mutation_tools_available
        )

        if may_propose:
            required_actions.append("Review the generated migration bundle before merge.")
        if not may_execute and may_propose:
            required_actions.append(
                "Keep write-back proposals in dry-run state or explicitly enable both write gates."
            )
        if not reasons:
            reasons.append("All evidence, validation, ownership, and write gates are satisfied.")
        return (
            SafetyDecision(
                may_generate=may_generate,
                may_propose_writeback=may_propose,
                may_execute_writeback=may_execute,
                reasons=tuple(reasons),
                required_human_actions=tuple(required_actions),
            ),
            tuple(dict.fromkeys(unresolved)),
        )
