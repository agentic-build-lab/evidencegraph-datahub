"""Verify EvidenceGraph reads through the pinned official DataHub MCP server."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from evidencegraph.context.mcp import DataHubMCPConfig, DataHubMCPProvider

SOURCE_URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,commerce.raw_orders,PROD)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gms-url",
        default=os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-output", type=Path, help="Optional ignored diagnostic payload.")
    parser.add_argument("--query", default="EvidenceGraph")
    return parser.parse_args()


def summarize(data: Any) -> dict[str, Any]:
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    urns: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "urn" and isinstance(item, str):
                    urns.add(item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    return {
        "payload_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        "urns": sorted(urns),
    }


def lineage_asset_urns(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return []
    envelope = data.get("downstreams")
    if not isinstance(envelope, dict):
        return []
    results = envelope.get("searchResults")
    if not isinstance(results, list):
        return []
    urns: list[str] = []
    for result in results:
        if not isinstance(result, dict) or not isinstance(result.get("entity"), dict):
            continue
        urn = result["entity"].get("urn")
        if isinstance(urn, str):
            urns.append(urn)
    return urns


async def collect(gms_url: str, query: str) -> tuple[dict[str, Any], dict[str, Any]]:
    config = DataHubMCPConfig(
        gms_url=gms_url,
        token=os.getenv("DATAHUB_GMS_TOKEN"),
        writes_enabled=False,
    )
    async with DataHubMCPProvider(config) as provider:
        search = await provider.search(query, num_results=20)
        entity = await provider.get_entities([SOURCE_URN])
        schema = await provider.list_schema_fields(SOURCE_URN, limit=100)
        lineage = await provider.get_lineage(
            SOURCE_URN,
            direction="downstream",
            max_hops=3,
            page_size=50,
        )
        column_lineage = await provider.get_lineage(
            SOURCE_URN,
            column="customer_tier",
            direction="downstream",
            max_hops=3,
            page_size=50,
        )
        downstream_urns = sorted(
            {urn for page in lineage.pages for urn in lineage_asset_urns(page.data)}
        )
        details = await provider.get_entities([SOURCE_URN, *downstream_urns])
    report = {
        "mcp_package": "mcp-server-datahub@0.6.0",
        "gms_url": gms_url,
        "search": {"is_error": search.is_error, **summarize(search.data)},
        "entity": {"is_error": entity.is_error, **summarize(entity.data)},
        "schema": {"is_error": schema.is_error, **summarize(schema.data)},
        "details": {"is_error": details.is_error, **summarize(details.data)},
        "lineage": {
            "complete": lineage.complete,
            "stop_reason": lineage.stop_reason,
            "next_offset": lineage.next_offset,
            "token_budgeted": lineage.token_budgeted,
            "pages": [
                {"is_error": page.is_error, **summarize(page.data)} for page in lineage.pages
            ],
        },
        "column_lineage": {
            "complete": column_lineage.complete,
            "stop_reason": column_lineage.stop_reason,
            "pages": [
                {"is_error": page.is_error, **summarize(page.data)} for page in column_lineage.pages
            ],
        },
        "server_log_policy": "discarded unless an explicit diagnostic stream is supplied",
    }
    raw = {
        "search": search.data,
        "entity": entity.data,
        "schema": schema.data,
        "details": details.data,
        "lineage_pages": [page.data for page in lineage.pages],
        "column_lineage_pages": [page.data for page in column_lineage.pages],
    }
    return report, raw


def main() -> None:
    args = parse_args()
    report, raw = asyncio.run(collect(args.gms_url, args.query))
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.raw_output is not None:
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.raw_output.write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(rendered)


if __name__ == "__main__":
    main()
