"""Deterministic blast-radius analysis over a DataHub context snapshot."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from evidencegraph.models import (
    Asset,
    AssetKind,
    ChangeRequest,
    ContextSnapshot,
    Criticality,
    Impact,
    LineageEdge,
    RiskLevel,
)


@dataclass(frozen=True)
class _TraversalState:
    urn: str
    field: str | None
    path: tuple[str, ...]
    observation_ids: tuple[str, ...]


_CRITICALITY_SCORE = {
    Criticality.CRITICAL: 60,
    Criticality.HIGH: 45,
    Criticality.MEDIUM: 30,
    Criticality.LOW: 15,
}

_KIND_SCORE = {
    AssetKind.DATASET: 10,
    AssetKind.DATA_JOB: 15,
    AssetKind.PIPELINE: 15,
    AssetKind.DASHBOARD: 20,
    AssetKind.CHART: 15,
    AssetKind.ML_FEATURE: 20,
    AssetKind.ML_FEATURE_TABLE: 20,
    AssetKind.ML_MODEL: 25,
    AssetKind.ML_MODEL_DEPLOYMENT: 30,
}


class ImpactEngine:
    """Enumerate all evidenced downstream paths and rank affected assets."""

    def analyze(self, change: ChangeRequest, snapshot: ContextSnapshot) -> tuple[Impact, ...]:
        assets = snapshot.asset_map()
        if change.asset_urn not in assets:
            raise ValueError(f"Changed asset is absent from context: {change.asset_urn}")

        adjacency: dict[str, list[LineageEdge]] = defaultdict(list)
        for edge in snapshot.lineage:
            adjacency[edge.upstream_urn].append(edge)

        queue: deque[_TraversalState] = deque(
            [_TraversalState(change.asset_urn, change.field, (change.asset_urn,), ())]
        )
        visited: set[tuple[str, str | None, tuple[str, ...]]] = set()
        paths: dict[str, list[tuple[str, ...]]] = defaultdict(list)
        fields: dict[str, set[str]] = defaultdict(set)
        observations: dict[str, set[str]] = defaultdict(set)

        while queue:
            state = queue.popleft()
            for edge in sorted(adjacency.get(state.urn, ()), key=lambda item: item.downstream_urn):
                downstream_fields = self._propagate_field(state.field, edge)
                if not downstream_fields:
                    continue
                for downstream_field in downstream_fields:
                    next_path = (*state.path, edge.downstream_urn)
                    key = (edge.downstream_urn, downstream_field, next_path)
                    if key in visited or edge.downstream_urn in state.path:
                        continue
                    visited.add(key)
                    paths[edge.downstream_urn].append(next_path)
                    if downstream_field:
                        fields[edge.downstream_urn].add(downstream_field)
                    next_observations = (*state.observation_ids, edge.source_observation_id)
                    observations[edge.downstream_urn].update(next_observations)
                    queue.append(
                        _TraversalState(
                            edge.downstream_urn,
                            downstream_field,
                            next_path,
                            next_observations,
                        )
                    )

        impacts = [
            self._build_impact(
                assets[urn],
                fields[urn],
                paths[urn],
                observations[urn],
            )
            for urn in paths
            if urn in assets
        ]
        return tuple(sorted(impacts, key=lambda impact: (-impact.risk_score, impact.asset_urn)))

    @staticmethod
    def _propagate_field(field: str | None, edge: LineageEdge) -> tuple[str | None, ...]:
        if not edge.field_mappings:
            return (None,)
        if field is None:
            return tuple(mapping.downstream_field for mapping in edge.field_mappings)
        return tuple(
            mapping.downstream_field
            for mapping in edge.field_mappings
            if mapping.upstream_field == field
        )

    @staticmethod
    def _build_impact(
        asset: Asset,
        affected_fields: set[str],
        paths: list[tuple[str, ...]],
        observation_ids: set[str],
    ) -> Impact:
        score = _CRITICALITY_SCORE[asset.criticality] + _KIND_SCORE[asset.kind]
        rationale = [
            f"{asset.criticality.value.title()}-criticality {asset.kind.value.replace('_', ' ')}.",
            f"Reachable through {len(paths)} evidenced downstream lineage path(s).",
        ]
        if asset.contract and affected_fields.intersection(asset.contract.required_fields):
            score += 20
            rationale.append("The affected field is required by an active data contract.")
        if asset.kind in {AssetKind.ML_MODEL, AssetKind.ML_MODEL_DEPLOYMENT}:
            rationale.append("The change can alter a production ML prediction dependency.")
        if asset.kind == AssetKind.DASHBOARD:
            rationale.append("The change can alter a human-facing decision surface.")
        if not asset.owners:
            score += 5
            rationale.append("No accountable owner was observed in DataHub.")
        score = min(score, 100)
        level = _risk_level(score)
        unique_paths = tuple(sorted(set(paths), key=lambda path: (len(path), path)))
        return Impact(
            asset_urn=asset.urn,
            asset_name=asset.name,
            kind=asset.kind,
            affected_fields=tuple(sorted(affected_fields)),
            paths=unique_paths,
            owners=asset.owners,
            risk_score=score,
            risk_level=level,
            rationale=tuple(rationale),
            source_observation_ids=tuple(sorted(observation_ids)),
        )


def _risk_level(score: int) -> RiskLevel:
    if score >= 90:
        return RiskLevel.BLOCKER
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 55:
        return RiskLevel.HIGH
    if score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
