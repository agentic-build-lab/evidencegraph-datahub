"""Idempotently load the EvidenceGraph miniature platform into DataHub Core."""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from datahub.emitter.mce_builder import make_schema_field_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    AuditStampClass,
    ChangeAuditStampsClass,
    CorpGroupInfoClass,
    DashboardInfoClass,
    DataContractPropertiesClass,
    DataContractStateClass,
    DataContractStatusClass,
    DataFlowInfoClass,
    DataJobInfoClass,
    DataJobInputOutputClass,
    DatasetLineageTypeClass,
    DatasetPropertiesClass,
    DateTypeClass,
    DocumentContentsClass,
    DocumentInfoClass,
    DocumentSourceClass,
    DocumentSourceTypeClass,
    DocumentStateClass,
    DocumentStatusClass,
    FineGrainedLineageClass,
    FineGrainedLineageDownstreamTypeClass,
    FineGrainedLineageUpstreamTypeClass,
    GlobalTagsClass,
    MLFeatureDataTypeClass,
    MLFeaturePropertiesClass,
    MLModelDeploymentPropertiesClass,
    MLModelPropertiesClass,
    NumberTypeClass,
    OtherSchemaClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
    RelatedAssetClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StatusClass,
    StringTypeClass,
    TagAssociationClass,
    TagPropertiesClass,
    UpstreamClass,
    UpstreamLineageClass,
    VersionTagClass,
)

from evidencegraph.endpoint_policy import UnsafeEndpointError, validate_bootstrap_target

ACTOR_URN = "urn:li:corpuser:evidencegraph"
DEMO_TAG_URN = "urn:li:tag:EvidenceGraphDemo"
REVIEW_TAG_URN = "urn:li:tag:EvidenceGraphReviewRequired"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=Path("fixtures/platform.json"))
    parser.add_argument(
        "--gms-url",
        default=os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"),
    )
    parser.add_argument(
        "--allow-remote-bootstrap",
        action="store_true",
        help="Explicitly authorize metadata writes to a non-local DataHub GMS endpoint.",
    )
    return parser.parse_args()


def emit_aspect(emitter: DatahubRestEmitter, urn: str, aspect: Any) -> None:
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=urn, aspect=aspect))


def ownership(owner_urns: Iterable[str]) -> OwnershipClass:
    return OwnershipClass(
        owners=[
            OwnerClass(owner=owner, type=OwnershipTypeClass.TECHNICAL_OWNER)
            for owner in sorted(set(owner_urns))
        ]
    )


def global_tags(tag_urns: Iterable[str], criticality: str) -> GlobalTagsClass:
    tags = {
        *tag_urns,
        DEMO_TAG_URN,
        f"urn:li:tag:Criticality{criticality.title()}",
    }
    return GlobalTagsClass(tags=[TagAssociationClass(tag=tag) for tag in sorted(tags)])


def schema_type(native_type: str) -> SchemaFieldDataTypeClass:
    normalized = native_type.upper()
    if any(token in normalized for token in ("INT", "DECIMAL", "NUMBER", "FLOAT")):
        return SchemaFieldDataTypeClass(type=NumberTypeClass())  # type: ignore[no-untyped-call]
    if any(token in normalized for token in ("DATE", "TIME")):
        return SchemaFieldDataTypeClass(type=DateTypeClass())  # type: ignore[no-untyped-call]
    return SchemaFieldDataTypeClass(type=StringTypeClass())  # type: ignore[no-untyped-call]


def emit_dataset(emitter: DatahubRestEmitter, asset: dict[str, Any]) -> int:
    urn = asset["urn"]
    custom_properties = {
        key: json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
        for key, value in asset.get("properties", {}).items()
    }
    if asset.get("contract"):
        custom_properties["data_contract_urn"] = asset["contract"]["contract_urn"]
    emit_aspect(
        emitter,
        urn,
        DatasetPropertiesClass(
            name=asset["name"],
            qualifiedName=asset["name"],
            description=asset["description"],
            customProperties=custom_properties,
        ),
    )
    fields = [
        SchemaFieldClass(
            fieldPath=field["name"],
            type=schema_type(field["native_type"]),
            nativeDataType=field["native_type"],
            nullable=field["nullable"],
            description=field.get("description"),
            globalTags=GlobalTagsClass(
                tags=[TagAssociationClass(tag=tag) for tag in field.get("tags", [])]
            )
            if field.get("tags")
            else None,
        )
        for field in asset.get("schema_fields", [])
    ]
    emit_aspect(
        emitter,
        urn,
        SchemaMetadataClass(
            schemaName=asset["name"],
            platform=f"urn:li:dataPlatform:{asset['platform']}",
            version=0,
            hash="",
            platformSchema=OtherSchemaClass(rawSchema="EvidenceGraph synthetic schema"),
            fields=fields,
        ),
    )
    emit_aspect(emitter, urn, ownership(asset["owners"]))
    emit_aspect(emitter, urn, global_tags(asset["tags"], asset["criticality"]))
    emit_aspect(emitter, urn, StatusClass(removed=False))
    return 5


def emit_dataset_lineage(
    emitter: DatahubRestEmitter,
    downstream_urn: str,
    upstream_edges: list[dict[str, Any]],
) -> int:
    fine_grained: list[FineGrainedLineageClass] = []
    upstreams: list[UpstreamClass] = []
    for edge in upstream_edges:
        upstreams.append(
            UpstreamClass(
                dataset=edge["upstream_urn"],
                type=DatasetLineageTypeClass.TRANSFORMED,
                auditStamp=AuditStampClass(time=int(time.time() * 1000), actor=ACTOR_URN),
            )
        )
        for mapping in edge["field_mappings"]:
            fine_grained.append(
                FineGrainedLineageClass(
                    upstreamType=FineGrainedLineageUpstreamTypeClass.FIELD_SET,
                    downstreamType=FineGrainedLineageDownstreamTypeClass.FIELD,
                    upstreams=[
                        make_schema_field_urn(edge["upstream_urn"], mapping["upstream_field"])
                    ],
                    downstreams=[
                        make_schema_field_urn(edge["downstream_urn"], mapping["downstream_field"])
                    ],
                    transformOperation=edge.get("transformation"),
                    confidenceScore=1.0,
                )
            )
    emit_aspect(
        emitter,
        downstream_urn,
        UpstreamLineageClass(upstreams=upstreams, fineGrainedLineages=fine_grained),
    )
    return 1


def emit_job(
    emitter: DatahubRestEmitter,
    asset: dict[str, Any],
    input_urns: list[str],
) -> int:
    job_urn = asset["urn"]
    flow_urn = job_urn.split(",build_customer_value)", maxsplit=1)[0].replace(
        "urn:li:dataJob:(", ""
    )
    emit_aspect(
        emitter,
        flow_urn,
        DataFlowInfoClass(
            name="daily_customer_value",
            description="EvidenceGraph Airflow demonstration flow.",
            customProperties={"evidencegraph_change": "EG-042"},
        ),
    )
    emit_aspect(
        emitter,
        job_urn,
        DataJobInfoClass(
            name=asset["name"],
            type="SQL",
            description=asset["description"],
            flowUrn=flow_urn,
            env="PROD",
            customProperties={
                key: str(value) for key, value in asset.get("properties", {}).items()
            },
        ),
    )
    emit_aspect(
        emitter,
        job_urn,
        DataJobInputOutputClass(inputDatasets=input_urns, outputDatasets=[]),
    )
    emit_aspect(emitter, job_urn, ownership(asset["owners"]))
    emit_aspect(emitter, job_urn, global_tags(asset["tags"], asset["criticality"]))
    return 5


def emit_dashboard(
    emitter: DatahubRestEmitter,
    asset: dict[str, Any],
    dataset_urns: list[str],
) -> int:
    audit = AuditStampClass(time=int(time.time() * 1000), actor=ACTOR_URN)
    emit_aspect(
        emitter,
        asset["urn"],
        DashboardInfoClass(
            title=asset["name"],
            description=asset["description"],
            lastModified=ChangeAuditStampsClass(created=audit, lastModified=audit),
            datasets=dataset_urns,
            customProperties={
                key: str(value) for key, value in asset.get("properties", {}).items()
            },
        ),
    )
    emit_aspect(emitter, asset["urn"], ownership(asset["owners"]))
    emit_aspect(emitter, asset["urn"], global_tags(asset["tags"], asset["criticality"]))
    return 3


def emit_ml_assets(emitter: DatahubRestEmitter, assets: dict[str, dict[str, Any]]) -> int:
    feature = assets["ml_feature"]
    model = assets["ml_model"]
    deployment = assets["ml_model_deployment"]
    source_dataset = "urn:li:dataset:(urn:li:dataPlatform:postgres,commerce.raw_orders,PROD)"
    feature_properties = {key: str(value) for key, value in feature.get("properties", {}).items()}
    if feature.get("contract"):
        feature_properties["feature_contract"] = json.dumps(feature["contract"], sort_keys=True)
        feature_properties["feature_contract_storage"] = (
            "structured custom property; DataHub Core v1.6 native data contracts "
            "do not target MLFeature entities"
        )
    emit_aspect(
        emitter,
        feature["urn"],
        MLFeaturePropertiesClass(
            description=feature["description"],
            dataType=MLFeatureDataTypeClass.NOMINAL,
            version=VersionTagClass(versionTag="1"),
            sources=[source_dataset],
            customProperties=feature_properties,
        ),
    )
    emit_aspect(emitter, feature["urn"], ownership(feature["owners"]))
    emit_aspect(
        emitter,
        feature["urn"],
        global_tags(feature["tags"], feature["criticality"]),
    )
    emit_aspect(
        emitter,
        deployment["urn"],
        MLModelDeploymentPropertiesClass(
            description=deployment["description"],
            version=VersionTagClass(versionTag="1"),
            status="IN_SERVICE",
            customProperties={
                key: str(value) for key, value in deployment.get("properties", {}).items()
            },
        ),
    )
    emit_aspect(emitter, deployment["urn"], ownership(deployment["owners"]))
    emit_aspect(
        emitter,
        deployment["urn"],
        global_tags(deployment["tags"], deployment["criticality"]),
    )
    emit_aspect(
        emitter,
        model["urn"],
        MLModelPropertiesClass(
            name=model["name"],
            description=model["description"],
            version=VersionTagClass(versionTag="4"),
            type="CLASSIFICATION",
            mlFeatures=[feature["urn"]],
            deployments=[deployment["urn"]],
            customProperties={
                key: str(value) for key, value in model.get("properties", {}).items()
            },
        ),
    )
    emit_aspect(emitter, model["urn"], ownership(model["owners"]))
    emit_aspect(emitter, model["urn"], global_tags(model["tags"], model["criticality"]))
    return 9


def emit_contracts(emitter: DatahubRestEmitter, assets: Iterable[dict[str, Any]]) -> int:
    emitted = 0
    for asset in assets:
        contract = asset.get("contract")
        if not contract or asset["kind"] != "dataset":
            continue
        contract_urn = contract["contract_urn"]
        emit_aspect(
            emitter,
            contract_urn,
            DataContractPropertiesClass(
                entity=asset["urn"],
                rawContract=json.dumps(contract, indent=2, sort_keys=True),
            ),
        )
        emit_aspect(
            emitter,
            contract_urn,
            DataContractStatusClass(state=DataContractStateClass.ACTIVE),
        )
        emitted += 2
    return emitted


def emit_document(emitter: DatahubRestEmitter, document: dict[str, Any]) -> int:
    audit = AuditStampClass(time=int(time.time() * 1000), actor=ACTOR_URN)
    emit_aspect(
        emitter,
        document["urn"],
        DocumentInfoClass(
            status=DocumentStatusClass(state=DocumentStateClass.PUBLISHED),
            contents=DocumentContentsClass(text=document["body"]),
            created=audit,
            lastModified=audit,
            title=document["title"],
            source=DocumentSourceClass(sourceType=DocumentSourceTypeClass.NATIVE),
            relatedAssets=[RelatedAssetClass(asset=urn) for urn in document["related_urns"]],
            customProperties={
                "evidencegraph_change": "EG-042",
                "structured_facts": json.dumps(document["facts"], sort_keys=True),
            },
        ),
    )
    return 1


def main() -> None:
    args = parse_args()
    try:
        validate_bootstrap_target(
            args.gms_url,
            allow_remote=args.allow_remote_bootstrap,
        )
    except UnsafeEndpointError as error:
        raise SystemExit(str(error)) from error
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    emitter = DatahubRestEmitter(
        gms_server=args.gms_url,
        token=os.getenv("DATAHUB_GMS_TOKEN"),
        timeout_sec=30,
    )
    emitter.test_connection()
    emitted = 0

    tag_urns = {
        DEMO_TAG_URN,
        REVIEW_TAG_URN,
        *(tag for asset in fixture["assets"] for tag in asset.get("tags", [])),
        *(f"urn:li:tag:Criticality{asset['criticality'].title()}" for asset in fixture["assets"]),
    }
    for tag_urn in sorted(tag_urns):
        emit_aspect(
            emitter,
            tag_urn,
            TagPropertiesClass(
                name=tag_urn.rsplit(":", maxsplit=1)[-1],
                description="EvidenceGraph demonstration metadata.",
                colorHex="#0EA5E9",
            ),
        )
        emitted += 1

    owner_urns = {owner for asset in fixture["assets"] for owner in asset.get("owners", [])}
    for owner_urn in sorted(owner_urns):
        display_name = owner_urn.rsplit(":", maxsplit=1)[-1].replace("-", " ").title()
        emit_aspect(
            emitter,
            owner_urn,
            CorpGroupInfoClass(
                admins=[],
                members=[],
                groups=[],
                displayName=display_name,
                description="Owner group for the EvidenceGraph miniature platform.",
            ),
        )
        emitted += 1

    by_kind = {asset["kind"]: asset for asset in fixture["assets"]}
    datasets = [asset for asset in fixture["assets"] if asset["kind"] == "dataset"]
    for asset in datasets:
        emitted += emit_dataset(emitter, asset)

    dataset_urns = {asset["urn"] for asset in datasets}
    lineage_by_downstream: dict[str, list[dict[str, Any]]] = {}
    for edge in fixture["lineage"]:
        if edge["upstream_urn"] in dataset_urns and edge["downstream_urn"] in dataset_urns:
            lineage_by_downstream.setdefault(edge["downstream_urn"], []).append(edge)
    for downstream_urn, upstream_edges in lineage_by_downstream.items():
        emitted += emit_dataset_lineage(emitter, downstream_urn, upstream_edges)

    fct_urn = "urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.fct_customer_value,PROD)"
    emitted += emit_job(emitter, by_kind["data_job"], [fct_urn])
    emitted += emit_dashboard(emitter, by_kind["dashboard"], [fct_urn])
    emitted += emit_ml_assets(emitter, by_kind)
    emitted += emit_contracts(emitter, fixture["assets"])
    for document in fixture["documents"]:
        emitted += emit_document(emitter, document)

    print(
        json.dumps(
            {
                "status": "ok",
                "gms_url": args.gms_url,
                "aspects_emitted": emitted,
                "assets": len(fixture["assets"]),
                "native_dataset_contracts": sum(
                    bool(asset.get("contract")) and asset["kind"] == "dataset"
                    for asset in fixture["assets"]
                ),
                "structured_feature_contracts": sum(
                    bool(asset.get("contract")) and asset["kind"] == "ml_feature"
                    for asset in fixture["assets"]
                ),
                "documents": len(fixture["documents"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
