from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast

import pytest

from evidencegraph.context import sdk as sdk_module
from evidencegraph.context.collector import LiveContextCollector, LiveContextError
from evidencegraph.context.provider import (
    ContextProvider,
    ContextResult,
    LineageDirection,
    LineageResult,
)
from evidencegraph.context.sdk import DataHubSDKError, DataHubSDKReader
from evidencegraph.models import AssetKind, ChangeKind, ChangeRequest, Criticality

SOURCE_URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,commerce.raw_orders,PROD)"
FEATURE_URN = "urn:li:mlFeature:(urn:li:mlFeatureTable:customer_features,tier_signal)"
MODEL_URN = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn_propensity,PROD)"
DEPLOYMENT_URN = (
    "urn:li:mlModelDeployment:(urn:li:dataPlatform:kubernetes,churn_api_prod,PROD)"
)
CONTRACT_URN = "urn:li:dataContract:raw-orders-v3"
DOCUMENT_URN = "urn:li:document:evidencegraph-migration-rfc"
UNKNOWN_URN = "urn:li:corpuser:unsupported-lineage-node"


def _change(*, field: str | None = "customer_tier") -> ChangeRequest:
    return ChangeRequest(
        change_id="EG-COVERAGE-001",
        asset_urn=SOURCE_URN,
        kind=ChangeKind.DROP_COLUMN if field else ChangeKind.CHANGE_PIPELINE,
        field=field,
        requested_by="urn:li:corpuser:platform-bot",
        reason="Verify a proposed source migration.",
        proposal_revision="coverage-rev-1",
        before_contract={"required_fields": ["customer_tier"]},
        after_contract={"required_fields": []},
    )


def _entity(urn: str, entity_type: str, name: str, platform: str) -> dict[str, Any]:
    return {
        "urn": urn,
        "type": entity_type,
        "properties": {"name": name, "description": f"Context for {name}."},
        "platform": {"name": platform},
        "ownership": {
            "owners": [{"owner": {"urn": "urn:li:corpGroup:data-platform"}}]
        },
        "tags": {"tags": [{"tag": {"urn": "urn:li:tag:CriticalityHigh"}}]},
    }


def _source_entity() -> dict[str, Any]:
    entity = _entity(SOURCE_URN, "DATASET", "commerce.raw_orders", "postgres")
    entity["properties"]["customProperties"] = [
        {"key": "data_contract_urn", "value": CONTRACT_URN}
    ]
    entity["schemaMetadata"] = {
        "fields": [
            {
                "fieldPath": "customer_tier",
                "nativeDataType": "VARCHAR",
                "nullable": False,
                "description": "Legacy customer tier.",
            },
            {"fieldPath": 42, "nativeDataType": "IGNORED"},
        ]
    }
    entity["relatedDocuments"] = {
        "documents": [{"urn": DOCUMENT_URN}, {"urn": 42}, "invalid"]
    }
    return entity


class _StubProvider:
    writes_enabled = False

    def __init__(
        self,
        *,
        include_unknown: bool = False,
        omit_feature_direct_edge: bool = False,
        source_error: bool = False,
        schema_error: bool = False,
        omit_source: bool = False,
    ) -> None:
        self.include_unknown = include_unknown
        self.omit_feature_direct_edge = omit_feature_direct_edge
        self.source_error = source_error
        self.schema_error = schema_error
        self.omit_source = omit_source
        self.entity_calls = 0
        self.lineage_calls: list[tuple[str, str, str | None]] = []
        self.entities = {
            SOURCE_URN: _source_entity(),
            FEATURE_URN: _entity(FEATURE_URN, "MLFEATURE", "legacy-tier", "feast"),
            MODEL_URN: _entity(MODEL_URN, "MLMODEL", "legacy-churn", "mlflow"),
            UNKNOWN_URN: _entity(UNKNOWN_URN, "CORP_USER", "unsupported", "datahub"),
        }

    async def get_entities(self, urns: Sequence[str]) -> ContextResult:
        self.entity_calls += 1
        result = [self.entities[urn] for urn in urns if urn in self.entities]
        if self.omit_source:
            result = [entity for entity in result if entity["urn"] != SOURCE_URN]
        return ContextResult(
            "get_entities",
            {"result": result},
            is_error=self.source_error and self.entity_calls == 1,
        )

    async def list_schema_fields(
        self,
        urn: str,
        *,
        keywords: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ContextResult:
        del keywords, limit, offset
        return ContextResult(
            "list_schema_fields",
            {"urn": urn, "fields": ["customer_tier"]},
            is_error=self.schema_error,
        )

    async def get_lineage(
        self,
        urn: str,
        *,
        column: str | None = None,
        query: str | None = None,
        filter: str | None = None,
        direction: LineageDirection = "downstream",
        max_hops: int = 3,
        page_size: int = 30,
        offset: int = 0,
        max_pages: int = 100,
    ) -> LineageResult:
        del query, filter, max_hops, page_size, offset, max_pages
        self.lineage_calls.append((urn, direction, column))
        entities: list[dict[str, Any]]
        if direction == "downstream":
            entities = [self.entities[FEATURE_URN], self.entities[MODEL_URN]]
            if self.include_unknown:
                entities.append(self.entities[UNKNOWN_URN])
        elif urn == FEATURE_URN:
            entities = [] if self.omit_feature_direct_edge else [self.entities[SOURCE_URN]]
        elif urn == MODEL_URN:
            entities = [self.entities[FEATURE_URN]]
        elif urn == UNKNOWN_URN:
            entities = [self.entities[SOURCE_URN]]
        else:
            entities = []
        results: list[dict[str, Any]] = []
        for entity in entities:
            item: dict[str, Any] = {"entity": entity}
            if column is not None and entity["urn"] == FEATURE_URN:
                item["lineageColumns"] = ["customer_tier_signal", 42]
            results.append(item)
        key = f"{direction}s"
        page = ContextResult(
            "get_lineage",
            {key: {"searchResults": results, "hasMore": False, "returned": len(results)}},
        )
        return LineageResult(direction, (page,), True, "exhausted", len(results))


class _StubSDK:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def ml_feature(self, urn: str) -> dict[str, Any]:
        self.calls.append(("ml_feature", urn))
        contract = {
            "contract_urn": "urn:li:dataContract:tier-signal-v1",
            "required_fields": ["customer_tier_signal"],
            "owner_urns": ["urn:li:corpGroup:ml-platform"],
            "rules": {"not_null": True},
        }
        return {
            "name": "customer_tier_signal",
            "description": "Feature derived from the legacy tier.",
            "customProperties": {
                "source_field": "customer_tier",
                "output_field": "customer_tier_signal",
                "feature_contract": json.dumps(contract),
            },
        }

    def ml_model(self, urn: str) -> dict[str, Any]:
        self.calls.append(("ml_model", urn))
        return {
            "name": "churn_propensity",
            "description": "Production churn model.",
            "deployments": [DEPLOYMENT_URN, 42],
            "mlFeatures": [FEATURE_URN, 42, "urn:li:mlFeature:missing"],
            "customProperties": {"framework": "xgboost"},
        }

    def ml_deployment(self, urn: str) -> dict[str, Any]:
        self.calls.append(("ml_deployment", urn))
        return {
            "description": "Serving endpoint for churn propensity.",
            "ownership": {
                "owners": [
                    {"owner": "urn:li:corpGroup:ml-platform"},
                    {"owner": 42},
                ]
            },
            "globalTags": {
                "tags": [
                    {"tag": "urn:li:tag:CriticalityHigh"},
                    {"tag": 42},
                ]
            },
            "customProperties": [{"key": "endpoint", "value": "churn-v1"}],
        }

    def data_contract(self, urn: str) -> dict[str, Any]:
        self.calls.append(("data_contract", urn))
        return {
            "rawContract": json.dumps(
                {
                    "required_fields": ["customer_tier"],
                    "owner_urns": ["urn:li:corpGroup:commerce"],
                    "status": "active",
                    "rules": {"nullable": False},
                }
            ),
            "status": {"state": "ACTIVE"},
        }

    def document(self, urn: str) -> dict[str, Any]:
        self.calls.append(("document", urn))
        return {
            "title": "Customer tier migration RFC",
            "contents": {"text": "Replace customer_tier only after consumers migrate."},
            "relatedAssets": [{"asset": SOURCE_URN}, {"asset": 42}, "invalid"],
            "customProperties": {
                "structured_facts": json.dumps(
                    {"approved_mapping": "bronze/silver/gold to segment_code"}
                )
            },
        }


def _collector(provider: _StubProvider, sdk: _StubSDK | None = None) -> LiveContextCollector:
    return LiveContextCollector(
        cast(ContextProvider, provider),
        cast(DataHubSDKReader, sdk or _StubSDK()),
    )


@pytest.mark.asyncio
async def test_collect_builds_evidence_addressed_ml_and_contract_context() -> None:
    provider = _StubProvider()
    sdk = _StubSDK()

    snapshot = await _collector(provider, sdk).collect(_change())

    assets = snapshot.asset_map()
    assert set(assets) == {SOURCE_URN, FEATURE_URN, MODEL_URN, DEPLOYMENT_URN}
    assert assets[SOURCE_URN].contract is not None
    assert assets[SOURCE_URN].contract.contract_urn == CONTRACT_URN
    assert assets[SOURCE_URN].schema_fields[0].nullable is False
    assert assets[FEATURE_URN].name == "customer_tier_signal"
    assert assets[FEATURE_URN].contract is not None
    assert assets[FEATURE_URN].contract.rules == {"not_null": True}
    assert assets[MODEL_URN].properties["framework"] == "xgboost"
    assert assets[DEPLOYMENT_URN].kind == AssetKind.ML_MODEL_DEPLOYMENT
    assert assets[DEPLOYMENT_URN].name == "churn-api-prod"
    assert assets[DEPLOYMENT_URN].owners == ("urn:li:corpGroup:ml-platform",)
    assert assets[DEPLOYMENT_URN].criticality == Criticality.HIGH
    assert assets[DEPLOYMENT_URN].properties == {"endpoint": "churn-v1"}

    edge_map = {(edge.upstream_urn, edge.downstream_urn): edge for edge in snapshot.lineage}
    source_feature = edge_map[(SOURCE_URN, FEATURE_URN)]
    assert source_feature.field_mappings[0].upstream_field == "customer_tier"
    assert source_feature.field_mappings[0].downstream_field == "customer_tier_signal"
    model_edge = edge_map[(FEATURE_URN, MODEL_URN)]
    assert model_edge.field_mappings[0].upstream_field == "customer_tier_signal"
    deployment_edge = edge_map[(MODEL_URN, DEPLOYMENT_URN)]
    assert deployment_edge.field_mappings[0].downstream_field == "customer_tier_signal"

    assert snapshot.completeness.is_complete
    assert snapshot.documents[0].title == "Customer tier migration RFC"
    assert snapshot.documents[0].related_urns == (SOURCE_URN,)
    assert snapshot.documents[0].facts == {
        "approved_mapping": "bronze/silver/gold to segment_code"
    }
    assert {observation.interface for observation in snapshot.observations} == {
        "DataHub MCP Server",
        "DataHub Python SDK",
    }
    assert set(sdk.calls) == {
        ("ml_feature", FEATURE_URN),
        ("ml_model", MODEL_URN),
        ("ml_deployment", DEPLOYMENT_URN),
        ("data_contract", CONTRACT_URN),
        ("document", DOCUMENT_URN),
    }


@pytest.mark.asyncio
async def test_collect_reports_unsupported_nodes_and_uses_feature_fallback_edge() -> None:
    provider = _StubProvider(include_unknown=True, omit_feature_direct_edge=True)

    snapshot = await _collector(provider).collect(_change(field=None))

    assert snapshot.completeness.frontier_exhausted is False
    assert snapshot.completeness.unsupported_entities == (UNKNOWN_URN,)
    assert all(call[2] is None for call in provider.lineage_calls)
    feature_edge = next(edge for edge in snapshot.lineage if edge.downstream_urn == FEATURE_URN)
    assert feature_edge.upstream_urn == SOURCE_URN
    assert feature_edge.field_mappings[0].upstream_field == "asset"
    assert feature_edge.transformation == "DataHub ML feature source relationship"


@pytest.mark.asyncio
@pytest.mark.parametrize("error_source", ["entity", "schema"])
async def test_collect_rejects_required_source_errors(error_source: str) -> None:
    provider = _StubProvider(
        source_error=error_source == "entity",
        schema_error=error_source == "schema",
    )

    with pytest.raises(LiveContextError, match="required source context"):
        await _collector(provider).collect(_change())


@pytest.mark.asyncio
async def test_collect_rejects_a_missing_changed_asset() -> None:
    provider = _StubProvider(omit_source=True)

    with pytest.raises(LiveContextError, match="changed asset was not returned"):
        await _collector(provider).collect(_change())


class _Aspect:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def to_obj(self) -> Any:
        return self.payload


def test_sdk_reader_uses_allowlisted_aspects_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses: dict[tuple[str, type[Any]], _Aspect | None] = {}
    graph_configs: list[dict[str, Any]] = []

    class StubGraph:
        def __init__(self, config: dict[str, Any]) -> None:
            graph_configs.append(config)

        def get_aspect(self, urn: str, aspect_type: type[Any]) -> _Aspect | None:
            return responses.get((urn, aspect_type))

    monkeypatch.setattr(sdk_module, "DatahubClientConfig", lambda **kwargs: kwargs)
    monkeypatch.setattr(sdk_module, "DataHubGraph", StubGraph)
    reader = DataHubSDKReader("http://datahub.test:8080", token="test-token")

    assert graph_configs == [
        {
            "server": "http://datahub.test:8080",
            "token": "test-token",
            "timeout_sec": 30,
            "datahub_component": "evidencegraph",
        }
    ]

    responses[(FEATURE_URN, sdk_module.MLFeaturePropertiesClass)] = _Aspect({"name": "tier"})
    responses[(MODEL_URN, sdk_module.MLModelPropertiesClass)] = _Aspect({"name": "churn"})
    responses[(DEPLOYMENT_URN, sdk_module.MLModelDeploymentPropertiesClass)] = _Aspect(
        {"description": "serving"}
    )
    responses[(DEPLOYMENT_URN, sdk_module.OwnershipClass)] = _Aspect(
        {"owners": [{"owner": "urn:li:corpGroup:ml"}]}
    )
    responses[(DEPLOYMENT_URN, sdk_module.GlobalTagsClass)] = _Aspect(["not-an-object"])
    responses[(CONTRACT_URN, sdk_module.DataContractPropertiesClass)] = _Aspect(
        {"rawContract": "{}"}
    )
    responses[(CONTRACT_URN, sdk_module.DataContractStatusClass)] = _Aspect(
        {"state": "ACTIVE"}
    )
    responses[(DOCUMENT_URN, sdk_module.DocumentInfoClass)] = _Aspect({"title": "RFC"})

    assert reader.ml_feature(FEATURE_URN) == {"name": "tier"}
    assert reader.ml_model(MODEL_URN) == {"name": "churn"}
    assert reader.ml_deployment(DEPLOYMENT_URN) == {
        "description": "serving",
        "ownership": {"owners": [{"owner": "urn:li:corpGroup:ml"}]},
        "globalTags": None,
    }
    assert reader.data_contract(CONTRACT_URN) == {
        "rawContract": "{}",
        "status": {"state": "ACTIVE"},
    }
    assert reader.document(DOCUMENT_URN) == {"title": "RFC"}

    responses[(FEATURE_URN, sdk_module.MLFeaturePropertiesClass)] = None
    with pytest.raises(DataHubSDKError, match="required MLFeaturePropertiesClass is absent"):
        reader.ml_feature(FEATURE_URN)

    responses[(FEATURE_URN, sdk_module.MLFeaturePropertiesClass)] = _Aspect(["invalid"])
    with pytest.raises(DataHubSDKError, match="returned a non-object payload"):
        reader.ml_feature(FEATURE_URN)
