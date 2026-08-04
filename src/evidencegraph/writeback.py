"""Create and execute allowlisted, idempotent DataHub MCP write-backs."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from evidencegraph.context.provider import ContextProvider, ContextResult, MutationResult
from evidencegraph.models import (
    ChangeRequest,
    EvidenceClaim,
    Impact,
    MutationReceipt,
    ValidationResult,
    WritebackProposal,
)

ALLOWED_MUTATION_TOOLS = frozenset({"add_tags", "update_description", "save_document"})
DEFAULT_WRITE_SCOPE_TAG = "urn:li:tag:EvidenceGraphDemo"
REVIEW_REQUIRED_TAG = "urn:li:tag:EvidenceGraphReviewRequired"
MAX_MUTATION_TARGETS = 16

_PROPOSAL_IDS = {
    "add_tags": "WB-TAG",
    "update_description": "WB-DESCRIPTION",
    "save_document": "WB-DOCUMENT",
}
_ARGUMENT_KEYS = {
    "add_tags": frozenset(
        {"entity_urns", "tag_urns", "scope_tag_urn", "target_set_sha256"}
    ),
    "update_description": frozenset(
        {
            "entity_urn",
            "operation",
            "description",
            "scope_tag_urn",
            "target_set_sha256",
        }
    ),
    "save_document": frozenset(
        {
            "document_type",
            "title",
            "content",
            "related_assets",
            "referenced_assets",
            "lookup_key",
            "ownership_marker",
            "scope_tag_urn",
            "target_set_sha256",
        }
    ),
}


def build_writeback_proposals(
    run_id: str,
    change: ChangeRequest,
    impacts: tuple[Impact, ...],
    claims: tuple[EvidenceClaim, ...],
    validations: tuple[ValidationResult, ...],
) -> tuple[WritebackProposal, ...]:
    affected_urns = [change.asset_urn, *(impact.asset_urn for impact in impacts)]
    mutable_urns = [
        change.asset_urn,
        *(impact.asset_urn for impact in impacts if impact.kind.value != "ml_model_deployment"),
    ]
    target_set_sha256 = _target_set_digest(mutable_urns)
    producer_target_sha256 = _target_set_digest([change.asset_urn])
    ownership_marker = hashlib.sha256(
        f"evidencegraph:{run_id}:{change.asset_urn}".encode()
    ).hexdigest()
    evidence_summary = _evidence_summary(
        run_id,
        change,
        impacts,
        claims,
        validations,
        ownership_marker=ownership_marker,
    )
    raw = (
        (
            "WB-TAG",
            "add_tags",
            {
                "entity_urns": mutable_urns,
                "tag_urns": [REVIEW_REQUIRED_TAG],
                "scope_tag_urn": DEFAULT_WRITE_SCOPE_TAG,
                "target_set_sha256": target_set_sha256,
            },
            "Mark every affected asset as requiring an evidence-reviewed migration.",
        ),
        (
            "WB-DESCRIPTION",
            "update_description",
            {
                "entity_urn": change.asset_urn,
                "operation": "append",
                "description": (
                    f"\n\n### EvidenceGraph change assurance -- {change.change_id}\n"
                    f"Run `{run_id}` found {len(impacts)} downstream assets. "
                    "See the saved EvidenceGraph document for claims and validation receipts.\n\n"
                    f"EvidenceGraph assurance marker: `{run_id}`"
                ),
                "scope_tag_urn": DEFAULT_WRITE_SCOPE_TAG,
                "target_set_sha256": producer_target_sha256,
            },
            "Leave durable change-review context on the producer asset.",
        ),
        (
            "WB-DOCUMENT",
            "save_document",
            {
                "document_type": "Analysis",
                "title": f"EvidenceGraph {change.change_id} evidence ledger ({run_id})",
                "content": evidence_summary,
                "related_assets": [change.asset_urn],
                "referenced_assets": affected_urns,
                "lookup_key": run_id,
                "ownership_marker": ownership_marker,
                "scope_tag_urn": DEFAULT_WRITE_SCOPE_TAG,
                "target_set_sha256": producer_target_sha256,
            },
            "Save a durable, searchable evidence ledger for future people and agents.",
        ),
    )
    proposals = []
    for proposal_id, tool, arguments, purpose in raw:
        if tool not in ALLOWED_MUTATION_TOOLS:
            raise ValueError(f"Mutation tool is not allowlisted: {tool}")
        proposals.append(
            WritebackProposal(
                proposal_id=proposal_id,
                tool=tool,
                arguments=arguments,
                purpose=purpose,
                idempotency_key=_proposal_idempotency_key(run_id, tool, arguments),
            )
        )
    return tuple(proposals)


class LiveWritebackError(RuntimeError):
    """Raised when a mutation fails its response or post-write readback gate."""


async def execute_writeback_proposals(
    provider: ContextProvider,
    proposals: Sequence[WritebackProposal],
    *,
    run_id: str,
    approval_granted: bool = False,
) -> tuple[MutationReceipt, ...]:
    """Execute policy-approved proposals and verify each mutation by reading it back."""

    if not approval_granted:
        raise LiveWritebackError("explicit approval is required for live metadata mutation")
    for proposal in proposals:
        _validate_proposal_integrity(proposal, run_id)

    receipts: list[MutationReceipt] = []
    for proposal in proposals:
        if proposal.tool == "add_tags":
            target_urns = _string_list(proposal.arguments, "entity_urns")
            before = await _validate_target_set(provider, proposal.arguments, target_urns)
            producer = target_urns[0]
            expected_tag = REVIEW_REQUIRED_TAG
            if all(_entity_has_tag(before.data, urn, expected_tag) for urn in target_urns):
                receipts.append(
                    _receipt(
                        proposal,
                        "skipped_idempotent_verified",
                        before.data,
                        target_urn=producer,
                    )
                )
                continue
            result = await provider.add_tags(
                _string_list(proposal.arguments, "tag_urns"),
                target_urns,
                dry_run=False,
            )
            _require_applied(proposal, result)
            readback = await provider.get_entities(target_urns)
            failed_targets = [
                urn for urn in target_urns if not _entity_has_tag(readback.data, urn, expected_tag)
            ]
            if failed_targets:
                raise LiveWritebackError(
                    f"tag mutation failed readback for {len(failed_targets)} target(s)"
                )
            receipts.append(
                _receipt(
                    proposal,
                    "applied_verified",
                    {"mutation": _mutation_data(result), "readback": readback.data},
                    target_urn=producer,
                )
            )
            continue

        if proposal.tool == "update_description":
            entity_urn = _string(proposal.arguments, "entity_urn")
            description = _string(proposal.arguments, "description")
            marker = description.rsplit("EvidenceGraph assurance marker: ", maxsplit=1)[-1]
            current = await _validate_target_set(provider, proposal.arguments, [entity_urn])
            if marker in _canonical(current.data):
                receipts.append(
                    _receipt(
                        proposal,
                        "skipped_idempotent_verified",
                        current.data,
                        target_urn=entity_urn,
                    )
                )
                continue
            result = await provider.update_description(
                entity_urn,
                description,
                operation="append",
                dry_run=False,
            )
            _require_applied(proposal, result)
            readback = await provider.get_entities([entity_urn])
            if marker not in _canonical(readback.data):
                raise LiveWritebackError("description mutation did not pass post-write readback")
            receipts.append(
                _receipt(
                    proposal,
                    "applied_verified",
                    {"mutation": _mutation_data(result), "readback": readback.data},
                    target_urn=entity_urn,
                )
            )
            continue

        lookup_key = _string(proposal.arguments, "lookup_key")
        expected_title = _string(proposal.arguments, "title")
        ownership_marker = _string(proposal.arguments, "ownership_marker")
        if ownership_marker in expected_title:
            raise LiveWritebackError("document ownership marker must be independent of its title")
        related_assets = _string_list(proposal.arguments, "related_assets")
        await _validate_target_set(provider, proposal.arguments, related_assets)
        existing = await provider.search_documents(lookup_key, num_results=20)
        existing_urn = _find_document_urn(existing.data, expected_title)
        if existing_urn is not None:
            existing_document = await provider.get_entities([existing_urn])
            marker_search = await provider.search_documents(ownership_marker, num_results=20)
            directly_verified = _document_matches(
                existing_document.data, existing_urn, ownership_marker, expected_title
            )
            index_verified = _find_document_urn(marker_search.data, expected_title) == existing_urn
            if not directly_verified and not index_verified:
                raise LiveWritebackError(
                    "refusing to overwrite a document without the exact EvidenceGraph marker"
                )
            receipts.append(
                _receipt(
                    proposal,
                    "skipped_idempotent_verified",
                    {
                        "entity": existing_document.data,
                        "marker_search": marker_search.data,
                    },
                    target_urn=existing_urn,
                )
            )
            continue
        result = await provider.save_document(
            "Analysis",
            expected_title,
            _string(proposal.arguments, "content"),
            urn=existing_urn,
            related_assets=related_assets,
            dry_run=False,
        )
        _require_applied(proposal, result)
        target_urn = _result_urn(result)
        if target_urn is None:
            raise LiveWritebackError("save_document returned no document URN")
        readback = await _read_document(
            provider,
            target_urn,
            lookup_key,
            expected_title,
            ownership_marker,
        )
        receipts.append(
            _receipt(
                proposal,
                "applied_verified",
                {"mutation": _mutation_data(result), "readback": readback},
                target_urn=target_urn,
            )
        )
    return tuple(receipts)


def _proposal_idempotency_key(
    run_id: str,
    tool: str,
    arguments: Mapping[str, Any],
) -> str:
    canonical = json.dumps(
        {"run_id": run_id, "tool": tool, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _validate_proposal_integrity(proposal: WritebackProposal, run_id: str) -> None:
    """Reject a tampered serialized proposal before the first provider call."""

    if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", run_id) is None:
        raise LiveWritebackError("run id does not match the bounded writeback schema")
    if proposal.tool not in ALLOWED_MUTATION_TOOLS:
        raise LiveWritebackError(f"mutation tool is not allowlisted: {proposal.tool}")
    if proposal.proposal_id != _PROPOSAL_IDS[proposal.tool]:
        raise LiveWritebackError("proposal id does not match its allowlisted tool schema")
    if not proposal.requires_human_approval:
        raise LiveWritebackError(
            "live metadata mutations must be marked as requiring explicit approval"
        )
    if set(proposal.arguments) != _ARGUMENT_KEYS[proposal.tool]:
        raise LiveWritebackError("proposal arguments do not match the allowlisted tool schema")
    expected_key = _proposal_idempotency_key(run_id, proposal.tool, proposal.arguments)
    if proposal.idempotency_key != expected_key:
        raise LiveWritebackError("proposal idempotency key does not match its canonical payload")

    if proposal.tool == "add_tags":
        targets = _string_list(proposal.arguments, "entity_urns")
        tags = _string_list(proposal.arguments, "tag_urns")
        if tags != [REVIEW_REQUIRED_TAG]:
            raise LiveWritebackError("tag mutation must add only the review-required tag")
        _validate_target_shape(proposal.arguments, targets)
        return

    if proposal.tool == "update_description":
        entity_urn = _string(proposal.arguments, "entity_urn")
        if _string(proposal.arguments, "operation") != "append":
            raise LiveWritebackError("description mutation must use append operation")
        description = _string(proposal.arguments, "description")
        marker = f"EvidenceGraph assurance marker: `{run_id}`"
        pattern = re.compile(
            rf"\A\n\n### EvidenceGraph change assurance -- [A-Za-z0-9._-]{{1,64}}\n"
            rf"Run `{re.escape(run_id)}` found \d{{1,4}} downstream assets\. "
            rf"See the saved EvidenceGraph document for claims and validation receipts\.\n\n"
            rf"{re.escape(marker)}\Z"
        )
        if pattern.fullmatch(description) is None:
            raise LiveWritebackError(
                "description mutation is missing the exact bounded assurance marker format"
            )
        _validate_target_shape(proposal.arguments, [entity_urn])
        return

    if _string(proposal.arguments, "document_type") != "Analysis":
        raise LiveWritebackError("document mutation must use the Analysis document type")
    related_assets = _string_list(proposal.arguments, "related_assets")
    referenced_assets = _string_list(proposal.arguments, "referenced_assets")
    if len(related_assets) != 1 or related_assets[0] not in referenced_assets:
        raise LiveWritebackError(
            "document mutation must relate exactly one producer included in referenced assets"
        )
    _validate_urns(referenced_assets, label="document referenced assets")
    if _string(proposal.arguments, "lookup_key") != run_id:
        raise LiveWritebackError("document lookup key must match the approved run id")
    title = _string(proposal.arguments, "title")
    title_match = re.fullmatch(
        rf"EvidenceGraph ([A-Za-z0-9._-]{{1,64}}) evidence ledger \({re.escape(run_id)}\)",
        title,
    )
    if title_match is None:
        raise LiveWritebackError("document title does not match the bounded run schema")
    producer = related_assets[0]
    expected_marker = hashlib.sha256(
        f"evidencegraph:{run_id}:{producer}".encode()
    ).hexdigest()
    ownership_marker = _string(proposal.arguments, "ownership_marker")
    if ownership_marker != expected_marker:
        raise LiveWritebackError("document ownership marker does not match its canonical owner")
    content = _string(proposal.arguments, "content")
    expected_prefix = (
        f"# EvidenceGraph evidence ledger -- {title_match.group(1)}\n\n"
        f"Run: `{run_id}`\nProducer: `{producer}`\n"
    )
    marker_line = f"EvidenceGraph ownership marker: `{ownership_marker}`"
    if not content.startswith(expected_prefix) or content.count(marker_line) != 1:
        raise LiveWritebackError(
            "document content must contain the exact canonical ownership marker"
        )
    _validate_target_shape(proposal.arguments, related_assets)


def _require_applied(proposal: WritebackProposal, result: MutationResult) -> None:
    if not result.applied or result.result is None or result.result.is_error:
        raise LiveWritebackError(f"DataHub MCP mutation failed: {proposal.tool}")


def _mutation_data(result: MutationResult) -> Any:
    return result.result.data if result.result is not None else None


def _receipt(
    proposal: WritebackProposal,
    status: str,
    response: Any,
    *,
    target_urn: str | None = None,
) -> MutationReceipt:
    canonical = _canonical(response)
    return MutationReceipt(
        proposal_id=proposal.proposal_id,
        tool=proposal.tool,
        status=status,
        response_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        target_urn=target_urn,
        executed_at=datetime.now(UTC),
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _result_urn(result: MutationResult) -> str | None:
    if result.result is None or not isinstance(result.result.data, dict):
        return None
    urn = result.result.data.get("urn")
    return urn if isinstance(urn, str) else None


def _find_document_urn(value: Any, expected_title: str) -> str | None:
    if isinstance(value, dict):
        urn = value.get("urn")
        info = value.get("info")
        title = info.get("title") if isinstance(info, dict) else value.get("title")
        if isinstance(urn, str) and urn.startswith("urn:li:document:") and title == expected_title:
            return urn
        for item in value.values():
            found = _find_document_urn(item, expected_title)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_document_urn(item, expected_title)
            if found is not None:
                return found
    return None


async def _read_document(
    provider: ContextProvider,
    target_urn: str,
    lookup_key: str,
    expected_title: str,
    ownership_marker: str,
) -> Any:
    for _ in range(4):
        entity = await provider.get_entities([target_urn])
        if _document_matches(entity.data, target_urn, ownership_marker, expected_title):
            return entity.data
        title_search = await provider.search_documents(lookup_key, num_results=20)
        marker_search = await provider.search_documents(ownership_marker, num_results=20)
        if (
            _find_document_urn(title_search.data, expected_title) == target_urn
            and _find_document_urn(marker_search.data, expected_title) == target_urn
        ):
            return {"title_search": title_search.data, "marker_search": marker_search.data}
        await asyncio.sleep(0.5)
    raise LiveWritebackError("document mutation did not pass post-write readback")


async def _validate_target_set(
    provider: ContextProvider,
    arguments: Mapping[str, Any],
    target_urns: Sequence[str],
) -> ContextResult:
    _validate_target_shape(arguments, target_urns)
    scope_tag = _string(arguments, "scope_tag_urn")
    before = await provider.get_entities(target_urns)
    outside_scope = [urn for urn in target_urns if not _entity_has_tag(before.data, urn, scope_tag)]
    if outside_scope:
        raise LiveWritebackError(
            f"refusing {len(outside_scope)} target(s) outside the configured write scope"
        )
    return before


def _validate_target_shape(
    arguments: Mapping[str, Any],
    target_urns: Sequence[str],
) -> None:
    if len(target_urns) > MAX_MUTATION_TARGETS or len(set(target_urns)) != len(target_urns):
        raise LiveWritebackError(
            f"mutation target set is duplicated or exceeds {MAX_MUTATION_TARGETS} entities"
        )
    _validate_urns(target_urns, label="mutation target set")
    observed_digest = _target_set_digest(target_urns)
    if observed_digest != _string(arguments, "target_set_sha256"):
        raise LiveWritebackError("mutation target-set digest does not match the approved plan")
    expected_scope = os.environ.get("EVIDENCEGRAPH_WRITE_SCOPE_TAG", DEFAULT_WRITE_SCOPE_TAG)
    scope_tag = _string(arguments, "scope_tag_urn")
    if scope_tag != expected_scope:
        raise LiveWritebackError("mutation scope tag does not match the operator policy")


def _validate_urns(target_urns: Sequence[str], *, label: str) -> None:
    if not target_urns or len(target_urns) > MAX_MUTATION_TARGETS:
        raise LiveWritebackError(f"{label} is empty or exceeds {MAX_MUTATION_TARGETS} entities")
    if len(set(target_urns)) != len(target_urns):
        raise LiveWritebackError(f"{label} contains duplicate entities")
    if any(
        not urn.startswith("urn:li:") or any(character.isspace() for character in urn)
        for urn in target_urns
    ):
        raise LiveWritebackError(f"{label} contains an invalid DataHub URN")


def _target_set_digest(target_urns: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(target_urns)).encode()).hexdigest()


def _entity_has_tag(data: Any, urn: str, tag_urn: str) -> bool:
    if not isinstance(data, dict) or not isinstance(data.get("result"), list):
        return False
    for entity in data["result"]:
        if isinstance(entity, dict) and entity.get("urn") == urn:
            return tag_urn in _canonical(entity)
    return False


def _document_matches(data: Any, urn: str, lookup_key: str, expected_title: str) -> bool:
    if isinstance(data, dict):
        candidate_urn = data.get("urn")
        info = data.get("info")
        title = info.get("title") if isinstance(info, dict) else data.get("title")
        if candidate_urn == urn and title == expected_title:
            marker_payload = dict(data)
            marker_payload.pop("urn", None)
            marker_payload.pop("title", None)
            if isinstance(info, dict):
                marker_info = dict(info)
                marker_info.pop("title", None)
                marker_payload["info"] = marker_info
            return lookup_key in _canonical(marker_payload)
        return any(
            _document_matches(value, urn, lookup_key, expected_title) for value in data.values()
        )
    if isinstance(data, list):
        return any(_document_matches(value, urn, lookup_key, expected_title) for value in data)
    return False


def _string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LiveWritebackError(f"proposal argument {key} must be a non-empty string")
    return value


def _string_list(arguments: Mapping[str, Any], key: str) -> list[str]:
    value = arguments.get(key)
    if not isinstance(value, list) or not value:
        raise LiveWritebackError(f"proposal argument {key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise LiveWritebackError(f"proposal argument {key} contains an invalid string")
    return value


def _evidence_summary(
    run_id: str,
    change: ChangeRequest,
    impacts: tuple[Impact, ...],
    claims: tuple[EvidenceClaim, ...],
    validations: tuple[ValidationResult, ...],
    *,
    ownership_marker: str,
) -> str:
    lines = [
        f"# EvidenceGraph evidence ledger -- {change.change_id}",
        "",
        f"Run: `{run_id}`",
        f"Producer: `{change.asset_urn}`",
        f"Change: `{change.kind.value}` / `{change.field or 'asset-level'}`",
        f"EvidenceGraph ownership marker: `{ownership_marker}`",
        "",
        "## Impact",
        "",
    ]
    lines.extend(
        f"- **{impact.risk_level.value} ({impact.risk_score})** `{impact.asset_urn}` "
        f"through {len(impact.paths)} path(s)."
        for impact in impacts
    )
    lines.extend(["", "## Evidence claims", ""])
    lines.extend(
        f"- `{claim.claim_id}` [{claim.status.value}, confidence {claim.confidence:.2f}] "
        f"{claim.statement}"
        for claim in claims
    )
    lines.extend(["", "## Validation receipts", ""])
    lines.extend(
        f"- `{result.validation_id}` **{result.status.value}** -- {result.details}"
        for result in validations
    )
    lines.append("")
    return "\n".join(lines)
