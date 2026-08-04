"""Narrow DataHub SDK reader for aspects not exposed by MCP Server 0.6.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub.metadata.schema_classes import (
    DataContractPropertiesClass,
    DataContractStatusClass,
    DocumentInfoClass,
    GlobalTagsClass,
    MLFeaturePropertiesClass,
    MLModelDeploymentPropertiesClass,
    MLModelPropertiesClass,
    OwnershipClass,
)


class DataHubSDKError(RuntimeError):
    """Raised when a required secondary aspect cannot be read safely."""


@dataclass(slots=True)
class DataHubSDKReader:
    """Read an allowlisted set of DataHub aspects using the official Python SDK."""

    server: str
    token: str | None = field(default=None, repr=False)
    _graph: DataHubGraph = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._graph = DataHubGraph(
            DatahubClientConfig(
                server=self.server,
                token=self.token,
                timeout_sec=30,
                datahub_component="evidencegraph",
            )
        )

    def ml_feature(self, urn: str) -> dict[str, Any]:
        return self._required(urn, MLFeaturePropertiesClass)

    def ml_model(self, urn: str) -> dict[str, Any]:
        return self._required(urn, MLModelPropertiesClass)

    def ml_deployment(self, urn: str) -> dict[str, Any]:
        properties = self._required(urn, MLModelDeploymentPropertiesClass)
        properties["ownership"] = self._optional(urn, OwnershipClass)
        properties["globalTags"] = self._optional(urn, GlobalTagsClass)
        return properties

    def data_contract(self, urn: str) -> dict[str, Any]:
        properties = self._required(urn, DataContractPropertiesClass)
        properties["status"] = self._optional(urn, DataContractStatusClass)
        return properties

    def document(self, urn: str) -> dict[str, Any]:
        return self._required(urn, DocumentInfoClass)

    def _required(self, urn: str, aspect_type: type[Any]) -> dict[str, Any]:
        value = self._graph.get_aspect(urn, aspect_type)
        if value is None:
            raise DataHubSDKError(f"required {aspect_type.__name__} is absent for {urn}")
        result = value.to_obj()
        if not isinstance(result, dict):
            raise DataHubSDKError(f"{aspect_type.__name__} returned a non-object payload")
        return result

    def _optional(self, urn: str, aspect_type: type[Any]) -> dict[str, Any] | None:
        value = self._graph.get_aspect(urn, aspect_type)
        if value is None:
            return None
        result = value.to_obj()
        return result if isinstance(result, dict) else None
