"""Collect a complete, evidence-addressed snapshot from live DataHub context."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from evidencegraph.context.provider import ContextProvider, ContextResult, LineageResult
from evidencegraph.context.sdk import DataHubSDKReader
from evidencegraph.models import (
    Asset,
    AssetKind,
    ChangeRequest,
    Completeness,
    ContextDocument,
    ContextSnapshot,
    Criticality,
    DataContract,
    FieldMapping,
    LineageEdge,
    Observation,
    SchemaField,
)

_TYPE_TO_KIND = {
    "DATASET": AssetKind.DATASET,
    "DATA_JOB": AssetKind.DATA_JOB,
    "DATA_FLOW": AssetKind.PIPELINE,
    "DASHBOARD": AssetKind.DASHBOARD,
    "CHART": AssetKind.CHART,
    "MLFEATURE": AssetKind.ML_FEATURE,
    "MLFEATURETABLE": AssetKind.ML_FEATURE_TABLE,
    "MLMODEL": AssetKind.ML_MODEL,
    "MLMODELDEPLOYMENT": AssetKind.ML_MODEL_DEPLOYMENT,
}


class LiveContextError(RuntimeError):
    """Raised when live context cannot satisfy EvidenceGraph's trust boundary."""


class LiveContextCollector:
    """Use MCP as the primary graph interface and SDK for allowlisted aspect gaps."""

    def __init__(self, provider: ContextProvider, sdk: DataHubSDKReader) -> None:
        self._provider = provider
        self._sdk = sdk
        self._observations: list[Observation] = []

    async def collect(self, change: ChangeRequest) -> ContextSnapshot:
        source_result = await self._provider.get_entities([change.asset_urn])
        self._observe(
            "DataHub MCP Server",
            "get_entities",
            change.asset_urn,
            source_result.data,
        )
        schema_result = await self._provider.list_schema_fields(change.asset_urn, limit=100)
        self._observe(
            "DataHub MCP Server",
            "list_schema_fields",
            change.asset_urn,
            schema_result.data,
            {"limit": 100},
        )
        lineage = await self._provider.get_lineage(
            change.asset_urn,
            direction="downstream",
            max_hops=3,
            page_size=50,
        )
        lineage_observations = self._observe_lineage(change.asset_urn, lineage)

        column_lineage: LineageResult | None = None
        if change.field:
            column_lineage = await self._provider.get_lineage(
                change.asset_urn,
                column=change.field,
                direction="downstream",
                max_hops=3,
                page_size=50,
            )
            self._observe_lineage(change.asset_urn, column_lineage, column=change.field)

        lineage_entities = _lineage_entities(lineage)
        downstream_urns = sorted(lineage_entities)
        details_result = await self._provider.get_entities([change.asset_urn, *downstream_urns])
        self._observe(
            "DataHub MCP Server",
            "get_entities",
            change.asset_urn,
            details_result.data,
            {"entity_count": len(downstream_urns) + 1, "purpose": "blast-radius enrichment"},
        )
        entities = {urn: dict(entity) for urn, entity in lineage_entities.items()}
        for urn, entity in _entity_map(details_result).items():
            entities.setdefault(urn, {}).update(entity)
        for urn, entity in _entity_map(source_result).items():
            entities.setdefault(urn, {}).update(entity)

        direct_results: dict[str, LineageResult] = {}
        for urn in downstream_urns:
            result = await self._provider.get_lineage(
                urn,
                direction="upstream",
                max_hops=1,
                page_size=50,
            )
            direct_results[urn] = result
            self._observe_lineage(urn, result)

        sdk_payloads = await self._sdk_enrich(entities)
        assets = self._build_assets(entities, sdk_payloads)
        deployment_edges, deployment_assets = self._deployment_context(sdk_payloads, assets)
        assets.extend(deployment_assets)

        affected_fields = _affected_fields(column_lineage)
        if change.field:
            affected_fields[change.asset_urn] = (change.field,)
        edges = self._build_edges(
            change,
            direct_results,
            affected_fields,
            lineage_observations,
            sdk_payloads,
        )
        edges.extend(deployment_edges)
        documents = await self._documents(entities.get(change.asset_urn, {}))

        all_lineage = [lineage, *direct_results.values()]
        if column_lineage is not None:
            all_lineage.append(column_lineage)
        unsupported = sorted(set(downstream_urns).difference(asset.urn for asset in assets))
        complete = all(result.complete for result in all_lineage) and not unsupported
        completeness = Completeness(
            requested_direction="downstream",
            requested_depth=3,
            pages_exhausted=all(result.complete for result in all_lineage),
            frontier_exhausted=complete,
            truncated=any(result.token_budgeted for result in all_lineage),
            unsupported_entities=tuple(unsupported),
            notes=(
                "MCP pagination and one-hop frontiers were exhausted.",
                (
                    "ML model deployment relationships were read from mlModelProperties via "
                    "the official DataHub Python SDK because MCP Server 0.6.0 does not expose "
                    "deployments as lineage nodes."
                ),
            ),
        )
        snapshot_seed = json.dumps(
            {
                "change": change.model_dump(mode="json"),
                "observations": [item.payload_sha256 for item in self._observations],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        snapshot_id = f"datahub-live-{hashlib.sha256(snapshot_seed.encode()).hexdigest()[:16]}"
        if change.asset_urn not in {asset.urn for asset in assets}:
            raise LiveContextError("changed asset was not returned by DataHub")
        if source_result.is_error or schema_result.is_error:
            raise LiveContextError("DataHub returned an error for required source context")
        return ContextSnapshot(
            snapshot_id=snapshot_id,
            assets=tuple(sorted(assets, key=lambda item: item.urn)),
            lineage=tuple(
                sorted(
                    _deduplicate_edges(edges),
                    key=lambda item: (item.upstream_urn, item.downstream_urn),
                )
            ),
            documents=tuple(documents),
            observations=tuple(self._observations),
            completeness=completeness,
        )

    async def _sdk_enrich(
        self, entities: Mapping[str, Mapping[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        payloads: dict[str, dict[str, Any]] = {}
        for urn, entity in entities.items():
            entity_type = entity.get("type")
            if entity_type == "MLFEATURE":
                payload = await asyncio.to_thread(self._sdk.ml_feature, urn)
                operation = "get_aspect:mlFeatureProperties"
            elif entity_type == "MLMODEL":
                payload = await asyncio.to_thread(self._sdk.ml_model, urn)
                operation = "get_aspect:mlModelProperties"
            else:
                continue
            payloads[urn] = payload
            self._observe("DataHub Python SDK", operation, urn, payload)

        for urn, entity in entities.items():
            contract_urn = _custom_properties(entity).get("data_contract_urn")
            if not contract_urn:
                continue
            payload = await asyncio.to_thread(self._sdk.data_contract, contract_urn)
            payloads[contract_urn] = payload
            self._observe(
                "DataHub Python SDK",
                "get_aspect:dataContractProperties",
                contract_urn,
                payload,
                {"contracted_entity": urn},
            )
        return payloads

    def _build_assets(
        self,
        entities: Mapping[str, Mapping[str, Any]],
        sdk_payloads: Mapping[str, Mapping[str, Any]],
    ) -> list[Asset]:
        assets: list[Asset] = []
        for urn, entity in entities.items():
            entity_type = entity.get("type") or _infer_type(urn)
            kind = _TYPE_TO_KIND.get(str(entity_type))
            if kind is None:
                continue
            props = _custom_properties(entity)
            description = _description(entity)
            name = _name(entity, urn)
            platform = _platform(entity, urn)
            contract = None
            contract_urn = props.get("data_contract_urn")
            if contract_urn and contract_urn in sdk_payloads:
                contract = _parse_native_contract(contract_urn, sdk_payloads[contract_urn])
            sdk_payload = sdk_payloads.get(urn)
            if sdk_payload:
                description = str(sdk_payload.get("description") or description)
                name = str(sdk_payload.get("name") or name)
                props.update(_string_mapping(sdk_payload.get("customProperties")))
                if kind == AssetKind.ML_FEATURE and props.get("feature_contract"):
                    contract = DataContract.model_validate_json(props["feature_contract"])
            assets.append(
                Asset(
                    urn=urn,
                    name=name,
                    kind=kind,
                    platform=platform,
                    description=description,
                    owners=_owners(entity),
                    tags=_tags(entity),
                    criticality=_criticality(_tags(entity)),
                    schema_fields=_schema_fields(entity),
                    contract=contract,
                    properties=props,
                )
            )
        return assets

    def _deployment_context(
        self,
        sdk_payloads: Mapping[str, Mapping[str, Any]],
        assets: Iterable[Asset],
    ) -> tuple[list[LineageEdge], list[Asset]]:
        edges: list[LineageEdge] = []
        deployment_assets: list[Asset] = []
        known_urns = {asset.urn for asset in assets}
        for model_urn, payload in sdk_payloads.items():
            if not model_urn.startswith("urn:li:mlModel:"):
                continue
            deployments = payload.get("deployments", [])
            if not isinstance(deployments, list):
                continue
            deployment_mappings: list[FieldMapping] = []
            features = payload.get("mlFeatures", [])
            if isinstance(features, list):
                for feature_urn in features:
                    if not isinstance(feature_urn, str):
                        continue
                    feature_payload = sdk_payloads.get(feature_urn)
                    if feature_payload is None:
                        continue
                    properties = _string_mapping(feature_payload.get("customProperties"))
                    output_field = properties.get("output_field")
                    if output_field:
                        deployment_mappings.append(
                            FieldMapping(
                                upstream_field=output_field,
                                downstream_field=output_field,
                            )
                        )
            model_observation = _observation_id_for(self._observations, model_urn)
            for deployment_urn in deployments:
                if not isinstance(deployment_urn, str):
                    continue
                deployment = self._sdk.ml_deployment(deployment_urn)
                self._observe(
                    "DataHub Python SDK",
                    "get_aspect:mlModelDeploymentProperties",
                    deployment_urn,
                    deployment,
                )
                if deployment_urn not in known_urns:
                    deployment_assets.append(_deployment_asset(deployment_urn, deployment))
                    known_urns.add(deployment_urn)
                edges.append(
                    LineageEdge(
                        upstream_urn=model_urn,
                        downstream_urn=deployment_urn,
                        field_mappings=tuple(deployment_mappings),
                        transformation="mlModelProperties.deployments relationship",
                        source_observation_id=model_observation,
                    )
                )
        return edges, deployment_assets

    def _build_edges(
        self,
        change: ChangeRequest,
        direct_results: Mapping[str, LineageResult],
        affected_fields: Mapping[str, tuple[str, ...]],
        root_observations: Mapping[str, str],
        sdk_payloads: Mapping[str, Mapping[str, Any]],
    ) -> list[LineageEdge]:
        edges: list[LineageEdge] = []
        allowed = {change.asset_urn, *direct_results}
        for downstream_urn, result in direct_results.items():
            upstreams = _lineage_entities(result)
            observation_id = _lineage_result_observation(self._observations, downstream_urn)
            for upstream_urn in sorted(set(upstreams).intersection(allowed)):
                mappings: tuple[FieldMapping, ...] = ()
                upstream_fields = affected_fields.get(upstream_urn)
                downstream_fields = affected_fields.get(downstream_urn)
                if upstream_fields and downstream_fields:
                    mappings = tuple(
                        FieldMapping(upstream_field=source, downstream_field=target)
                        for source, target in zip(upstream_fields, downstream_fields, strict=False)
                    )
                feature_payload = sdk_payloads.get(downstream_urn)
                if downstream_urn.startswith("urn:li:mlFeature:") and feature_payload:
                    feature_properties = _string_mapping(feature_payload.get("customProperties"))
                    source_field = feature_properties.get("source_field")
                    output_field = feature_properties.get("output_field")
                    if source_field and output_field:
                        mappings = (
                            FieldMapping(
                                upstream_field=source_field,
                                downstream_field=output_field,
                            ),
                        )
                if downstream_urn.startswith("urn:li:mlModel:"):
                    feature_payload = sdk_payloads.get(upstream_urn)
                    if feature_payload:
                        properties = _string_mapping(feature_payload.get("customProperties"))
                        feature_field = properties.get("output_field")
                        if feature_field:
                            mappings = (
                                FieldMapping(
                                    upstream_field=feature_field,
                                    downstream_field=feature_field,
                                ),
                            )
                edges.append(
                    LineageEdge(
                        upstream_urn=upstream_urn,
                        downstream_urn=downstream_urn,
                        field_mappings=mappings,
                        transformation="DataHub direct upstream relationship",
                        source_observation_id=observation_id,
                    )
                )

        feature_assets = [urn for urn in direct_results if urn.startswith("urn:li:mlFeature:")]
        for feature_urn in feature_assets:
            if any(edge.downstream_urn == feature_urn for edge in edges):
                continue
            feature_observation_id = root_observations.get(feature_urn)
            if feature_observation_id is None:
                continue
            edges.append(
                LineageEdge(
                    upstream_urn=change.asset_urn,
                    downstream_urn=feature_urn,
                    field_mappings=(
                        FieldMapping(
                            upstream_field=change.field or "asset",
                            downstream_field=_urn_name(feature_urn),
                        ),
                    ),
                    transformation="DataHub ML feature source relationship",
                    source_observation_id=feature_observation_id,
                )
            )
        return edges

    async def _documents(self, source: Mapping[str, Any]) -> list[ContextDocument]:
        related = source.get("relatedDocuments")
        if not isinstance(related, dict) or not isinstance(related.get("documents"), list):
            return []
        documents: list[ContextDocument] = []
        for item in related["documents"]:
            if not isinstance(item, dict) or not isinstance(item.get("urn"), str):
                continue
            urn = item["urn"]
            payload = await asyncio.to_thread(self._sdk.document, urn)
            observation = self._observe(
                "DataHub Python SDK", "get_aspect:documentInfo", urn, payload
            )
            custom = _string_mapping(payload.get("customProperties"))
            facts_raw = custom.get("structured_facts", "{}")
            facts = json.loads(facts_raw)
            contents = payload.get("contents")
            body = contents.get("text", "") if isinstance(contents, dict) else ""
            related_assets = payload.get("relatedAssets", [])
            related_urns = tuple(
                value["asset"]
                for value in related_assets
                if isinstance(value, dict) and isinstance(value.get("asset"), str)
            )
            documents.append(
                ContextDocument(
                    urn=urn,
                    title=str(payload.get("title") or urn),
                    body=str(body),
                    related_urns=related_urns,
                    facts=facts if isinstance(facts, dict) else {},
                    source_observation_id=observation.observation_id,
                )
            )
        return documents

    def _observe_lineage(
        self, urn: str, result: LineageResult, *, column: str | None = None
    ) -> dict[str, str]:
        by_entity: dict[str, str] = {}
        for index, page in enumerate(result.pages):
            observation = self._observe(
                "DataHub MCP Server",
                "get_lineage",
                urn,
                page.data,
                {
                    "direction": result.direction,
                    "page": index + 1,
                    "complete": result.complete,
                    "stop_reason": result.stop_reason,
                    "column": column,
                },
            )
            for entity_urn in _lineage_entities_from_data(page.data, result.direction):
                by_entity[entity_urn] = observation.observation_id
        return by_entity

    def _observe(
        self,
        interface: str,
        operation: str,
        object_urn: str | None,
        payload: Any,
        details: Mapping[str, Any] | None = None,
    ) -> Observation:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        recorded_details = dict(details or {})
        recorded_details["interface_version"] = (
            "mcp-server-datahub@0.6.0"
            if interface == "DataHub MCP Server"
            else "acryl-datahub@1.6.0"
        )
        argument_material = json.dumps(
            {
                "operation": operation,
                "object_urn": object_urn,
                "details": details or {},
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        recorded_details["arguments_sha256"] = hashlib.sha256(
            argument_material.encode()
        ).hexdigest()
        seed = f"{interface}:{operation}:{object_urn}:{digest}"
        identifier = hashlib.sha256(seed.encode()).hexdigest()[:12].upper()
        observation = Observation(
            observation_id=f"OBS-{identifier}",
            interface=interface,
            operation=operation,
            object_urn=object_urn,
            locator=f"{interface}:{operation}:{object_urn or 'global'}",
            payload_sha256=digest,
            observed_at=datetime.now(UTC),
            details=recorded_details,
        )
        self._observations.append(observation)
        return observation


def _entity_map(result: ContextResult) -> dict[str, dict[str, Any]]:
    if result.is_error or not isinstance(result.data, dict):
        return {}
    values = result.data.get("result")
    if not isinstance(values, list):
        return {}
    entities: dict[str, dict[str, Any]] = {}
    for value in values:
        if isinstance(value, dict):
            urn = value.get("urn")
            if isinstance(urn, str):
                entities[urn] = dict(value)
    return entities


def _lineage_entities(result: LineageResult) -> dict[str, dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}
    for page in result.pages:
        for urn, entity in _lineage_entities_from_data(page.data, result.direction).items():
            entities[urn] = entity
    return entities


def _lineage_entities_from_data(data: Any, direction: str) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict):
        return {}
    envelope = data.get(f"{direction}s")
    if not isinstance(envelope, dict) or not isinstance(envelope.get("searchResults"), list):
        return {}
    entities: dict[str, dict[str, Any]] = {}
    for result in envelope["searchResults"]:
        if not isinstance(result, dict) or not isinstance(result.get("entity"), dict):
            continue
        entity = result["entity"]
        urn = entity.get("urn")
        if isinstance(urn, str):
            entities[urn] = entity
    return entities


def _affected_fields(result: LineageResult | None) -> dict[str, tuple[str, ...]]:
    if result is None:
        return {}
    fields: dict[str, tuple[str, ...]] = {}
    for page in result.pages:
        if not isinstance(page.data, dict):
            continue
        envelope = page.data.get("downstreams")
        if not isinstance(envelope, dict) or not isinstance(envelope.get("searchResults"), list):
            continue
        search_results = envelope.get("searchResults")
        if not isinstance(search_results, list):
            continue
        for item in search_results:
            if not isinstance(item, dict) or not isinstance(item.get("entity"), dict):
                continue
            entity = item.get("entity")
            if not isinstance(entity, dict):
                continue
            urn = entity.get("urn")
            columns = item.get("lineageColumns")
            if isinstance(urn, str) and isinstance(columns, list):
                fields[urn] = tuple(value for value in columns if isinstance(value, str))
    return fields


def _custom_properties(entity: Mapping[str, Any]) -> dict[str, str]:
    properties = entity.get("properties")
    if not isinstance(properties, dict):
        return {}
    return _string_mapping(properties.get("customProperties"))


def _string_mapping(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    if not isinstance(value, list):
        return {}
    result: dict[str, str] = {}
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            result[item["key"]] = str(item.get("value", ""))
    return result


def _name(entity: Mapping[str, Any], urn: str) -> str:
    properties = entity.get("properties")
    if isinstance(properties, dict):
        property_name = properties.get("name")
        if isinstance(property_name, str):
            return property_name
    entity_name = entity.get("name")
    if isinstance(entity_name, str):
        return entity_name
    if isinstance(entity.get("description"), str) and not entity.get("name"):
        return _urn_name(urn)
    return _urn_name(urn)


def _description(entity: Mapping[str, Any]) -> str:
    properties = entity.get("properties")
    if isinstance(properties, dict):
        description = properties.get("description")
        if isinstance(description, str):
            return description
    return str(entity.get("description") or "")


def _platform(entity: Mapping[str, Any], urn: str) -> str:
    platform = entity.get("platform")
    if isinstance(platform, dict):
        platform_name = platform.get("name")
        if isinstance(platform_name, str):
            return platform_name
    data_flow = entity.get("dataFlow")
    if isinstance(data_flow, dict):
        nested = data_flow.get("platform")
        if isinstance(nested, dict):
            nested_name = nested.get("name")
            if isinstance(nested_name, str):
                return nested_name
    marker = "urn:li:dataPlatform:"
    if marker in urn:
        return urn.split(marker, maxsplit=1)[1].split(",", maxsplit=1)[0]
    return urn.split(":", maxsplit=3)[2] if urn.count(":") >= 3 else "datahub"


def _owners(entity: Mapping[str, Any]) -> tuple[str, ...]:
    ownership = entity.get("ownership")
    if not isinstance(ownership, dict) or not isinstance(ownership.get("owners"), list):
        return ()
    result: set[str] = set()
    for item in ownership["owners"]:
        if not isinstance(item, dict) or not isinstance(item.get("owner"), dict):
            continue
        urn = item["owner"].get("urn")
        if isinstance(urn, str):
            result.add(urn)
    return tuple(sorted(result))


def _tags(entity: Mapping[str, Any]) -> tuple[str, ...]:
    container = entity.get("tags")
    if not isinstance(container, dict) or not isinstance(container.get("tags"), list):
        return ()
    result: set[str] = set()
    for item in container["tags"]:
        if not isinstance(item, dict) or not isinstance(item.get("tag"), dict):
            continue
        urn = item["tag"].get("urn")
        if isinstance(urn, str):
            result.add(urn)
    return tuple(sorted(result))


def _criticality(tags: Iterable[str]) -> Criticality:
    values = set(tags)
    for level in Criticality:
        if f"urn:li:tag:Criticality{level.value.title()}" in values:
            return level
    return Criticality.MEDIUM


def _schema_fields(entity: Mapping[str, Any]) -> tuple[SchemaField, ...]:
    metadata = entity.get("schemaMetadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("fields"), list):
        return ()
    fields: list[SchemaField] = []
    for item in metadata["fields"]:
        if not isinstance(item, dict) or not isinstance(item.get("fieldPath"), str):
            continue
        fields.append(
            SchemaField(
                name=item["fieldPath"],
                native_type=str(item.get("nativeDataType") or "UNKNOWN"),
                nullable=item.get("nullable") is not False,
                description=item.get("description")
                if isinstance(item.get("description"), str)
                else None,
            )
        )
    return tuple(sorted(fields, key=lambda item: item.name))


def _parse_native_contract(urn: str, payload: Mapping[str, Any]) -> DataContract:
    raw = payload.get("rawContract")
    if not isinstance(raw, str):
        raise LiveContextError(f"DataHub contract {urn} has no rawContract")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise LiveContextError(f"DataHub contract {urn} rawContract is not an object")
    parsed["contract_urn"] = urn
    return DataContract.model_validate(parsed)


def _deployment_asset(urn: str, payload: Mapping[str, Any]) -> Asset:
    ownership = payload.get("ownership")
    owners: list[str] = []
    if isinstance(ownership, dict) and isinstance(ownership.get("owners"), list):
        owners = [
            item["owner"]
            for item in ownership["owners"]
            if isinstance(item, dict) and isinstance(item.get("owner"), str)
        ]
    global_tags = payload.get("globalTags")
    tags: list[str] = []
    if isinstance(global_tags, dict) and isinstance(global_tags.get("tags"), list):
        tags = [
            item["tag"]
            for item in global_tags["tags"]
            if isinstance(item, dict) and isinstance(item.get("tag"), str)
        ]
    return Asset(
        urn=urn,
        name=_deployment_name(urn).replace("_", "-"),
        kind=AssetKind.ML_MODEL_DEPLOYMENT,
        platform=_platform({}, urn),
        description=str(payload.get("description") or ""),
        owners=tuple(sorted(owners)),
        tags=tuple(sorted(tags)),
        criticality=_criticality(tags),
        properties=_string_mapping(payload.get("customProperties")),
    )


def _infer_type(urn: str) -> str | None:
    mapping = {
        "urn:li:dataset:": "DATASET",
        "urn:li:dataJob:": "DATA_JOB",
        "urn:li:dataFlow:": "DATA_FLOW",
        "urn:li:dashboard:": "DASHBOARD",
        "urn:li:chart:": "CHART",
        "urn:li:mlFeature:": "MLFEATURE",
        "urn:li:mlFeatureTable:": "MLFEATURETABLE",
        "urn:li:mlModel:": "MLMODEL",
        "urn:li:mlModelDeployment:": "MLMODELDEPLOYMENT",
    }
    return next((value for prefix, value in mapping.items() if urn.startswith(prefix)), None)


def _urn_name(urn: str) -> str:
    value = urn.rsplit(",", maxsplit=1)[-1].rstrip(")")
    if value == urn:
        value = urn.rsplit(":", maxsplit=1)[-1]
    return value


def _deployment_name(urn: str) -> str:
    parts = urn.rsplit(",", maxsplit=2)
    if len(parts) == 3:
        return parts[1]
    return _urn_name(urn)


def _observation_id_for(observations: Iterable[Observation], urn: str) -> str:
    for observation in reversed(tuple(observations)):
        if observation.object_urn == urn:
            return observation.observation_id
    raise LiveContextError(f"no observation supports relationship from {urn}")


def _lineage_result_observation(observations: Iterable[Observation], urn: str) -> str:
    for observation in reversed(tuple(observations)):
        if observation.object_urn == urn and observation.operation == "get_lineage":
            return observation.observation_id
    raise LiveContextError(f"no lineage observation was recorded for {urn}")


def _deduplicate_edges(edges: Iterable[LineageEdge]) -> tuple[LineageEdge, ...]:
    unique: dict[tuple[str, str], LineageEdge] = {}
    for edge in edges:
        unique[(edge.upstream_urn, edge.downstream_urn)] = edge
    return tuple(unique.values())
