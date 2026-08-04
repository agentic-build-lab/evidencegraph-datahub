"""EvidenceGraph command-line interface."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from evidencegraph.ablation import load_truth_manifest, run_ablation
from evidencegraph.closure import verify_fresh_graph_closure
from evidencegraph.context.collector import LiveContextCollector
from evidencegraph.context.mcp import DataHubMCPConfig, DataHubMCPProvider
from evidencegraph.context.sdk import DataHubSDKReader
from evidencegraph.models import EvidenceLedger, MutationReceipt
from evidencegraph.orchestrator import EvidenceGraphAgent, load_change, load_snapshot
from evidencegraph.writeback import execute_writeback_proposals

app = typer.Typer(
    name="evidencegraph",
    help="Compile a DataHub-grounded data change into a validated migration bundle.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def analyze(
    change: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    context: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option(file_okay=False)] = Path("outputs/runs"),
    warehouse_setup: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = Path(
        "fixtures/warehouse/setup.sql"
    ),
    apply: Annotated[
        bool, typer.Option(help="Request live write-back after all policy gates.")
    ] = False,
) -> None:
    """Analyze a proposed change against a captured DataHub context snapshot."""

    agent = EvidenceGraphAgent(warehouse_setup)
    ledger, paths = agent.run(
        load_change(change),
        load_snapshot(context),
        output_root=output,
        apply_requested=apply,
        mutation_tools_available=False,
    )
    _print_result(ledger, paths.root, paths.ledger_json)


@app.command("analyze-live")
def analyze_live(
    change: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    gms_url: Annotated[
        str, typer.Option(help="DataHub GMS URL; token is read only from DATAHUB_GMS_TOKEN.")
    ] = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"),
    output: Annotated[Path, typer.Option(file_okay=False)] = Path("outputs/runs"),
    warehouse_setup: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = Path(
        "fixtures/warehouse/setup.sql"
    ),
    apply: Annotated[
        bool,
        typer.Option(
            help=(
                "Apply allowlisted MCP write-backs after every policy gate. Also requires "
                "EVIDENCEGRAPH_ENABLE_WRITES=true."
            )
        ),
    ] = False,
) -> None:
    """Analyze a change using live DataHub MCP context and SDK aspect enrichment."""

    change_request = load_change(change)
    writes_enabled = apply and os.getenv("EVIDENCEGRAPH_ENABLE_WRITES", "").lower() == "true"
    config = DataHubMCPConfig(
        gms_url=gms_url,
        token=os.getenv("DATAHUB_GMS_TOKEN"),
        writes_enabled=writes_enabled,
    )

    async def run_live() -> tuple[EvidenceLedger, Path, Path]:
        async with DataHubMCPProvider(config) as provider:
            collector = LiveContextCollector(
                provider,
                DataHubSDKReader(gms_url, os.getenv("DATAHUB_GMS_TOKEN")),
            )
            snapshot = await collector.collect(change_request)
            agent = EvidenceGraphAgent(warehouse_setup)
            ledger, paths = agent.run(
                change_request,
                snapshot,
                output_root=output,
                apply_requested=apply,
                mutation_tools_available=provider.writes_enabled,
            )
            snapshot_path = paths.root / "context-snapshot.json"
            snapshot_path.write_text(
                snapshot.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            if ledger.safety_decision.may_execute_writeback:
                receipts = await execute_writeback_proposals(
                    provider,
                    ledger.writeback_proposals,
                    run_id=ledger.run_id,
                    approval_granted=apply,
                )
                ledger = ledger.model_copy(update={"mutation_receipts": receipts})
                paths = agent.persist(output, ledger)
            return ledger, paths.root, paths.ledger_json

    ledger, root, ledger_json = asyncio.run(run_live())
    _print_result(ledger, root, ledger_json)


def _print_result(ledger: EvidenceLedger, root: Path, ledger_json: Path) -> None:
    table = Table(title=f"EvidenceGraph {ledger.run_id}")
    table.add_column("Risk", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Affected asset")
    table.add_column("Paths", justify="right")
    for impact in ledger.impacts:
        table.add_row(
            impact.risk_level.value,
            str(impact.risk_score),
            impact.asset_name,
            str(len(impact.paths)),
        )
    console.print(table)
    console.print(
        f"[green]Bundle written:[/green] {root}\n"
        f"[green]Ledger:[/green] {ledger_json}\n"
        f"[yellow]Live write-back:[/yellow] "
        f"{'allowed' if ledger.safety_decision.may_execute_writeback else 'blocked / dry-run'}"
    )


@app.command("demo")
def demo(
    output: Annotated[Path, typer.Option(file_okay=False)] = Path("outputs/runs"),
) -> None:
    """Run the deterministic flagship scenario without credentials."""

    analyze(
        change=Path("fixtures/changes/drop_customer_tier.json"),
        context=Path("fixtures/platform.json"),
        output=output,
        warehouse_setup=Path("fixtures/warehouse/setup.sql"),
        apply=False,
    )


@app.command("ablation")
def ablation(
    change: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = Path(
        "fixtures/changes/drop_customer_tier.json"
    ),
    context: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = Path(
        "fixtures/platform.json"
    ),
    truth: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = Path(
        "fixtures/truth_manifest.json"
    ),
) -> None:
    """Compare full DataHub context against a repository-only dependency view."""

    result = run_ablation(
        load_change(change),
        load_snapshot(context),
        load_truth_manifest(truth),
    )
    console.print(JSON.from_data(result.to_dict()))


@app.command("verify-closure")
def verify_closure(
    before: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    after: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    ledger: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    patch: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option(dir_okay=False)] = Path("outputs/closure-receipt.json"),
    applied_at: Annotated[str, typer.Option()] = "2026-08-03T12:30:00+00:00",
) -> None:
    """Refuse stale closure or emit a receipt from a newer, complete graph."""

    evidence = EvidenceLedger.model_validate_json(ledger.read_text(encoding="utf-8"))
    timestamp = datetime.fromisoformat(applied_at.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    receipt = verify_fresh_graph_closure(
        evidence.change,
        load_snapshot(before),
        load_snapshot(after),
        evidence.validations,
        patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
        applied_at=timestamp,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(receipt.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    console.print(JSON.from_data(receipt.model_dump(mode="json")))


@app.command("verify-writeback-retry")
def verify_writeback_retry(
    ledger: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    gms_url: Annotated[str, typer.Option()] = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"),
    output: Annotated[Path, typer.Option(dir_okay=False)] = Path(
        "outputs/writeback-retry-receipts.json"
    ),
    apply: Annotated[bool, typer.Option(help="Confirm the live idempotency probe.")] = False,
) -> None:
    """Re-run an approved proposal set and prove every mutation is a verified no-op."""

    writes_enabled = apply and os.getenv("EVIDENCEGRAPH_ENABLE_WRITES", "").lower() == "true"
    if not writes_enabled:
        raise typer.BadParameter(
            "Retry verification requires --apply and EVIDENCEGRAPH_ENABLE_WRITES=true."
        )
    evidence = EvidenceLedger.model_validate_json(ledger.read_text(encoding="utf-8"))
    config = DataHubMCPConfig(
        gms_url=gms_url,
        token=os.getenv("DATAHUB_GMS_TOKEN"),
        writes_enabled=True,
    )

    async def retry() -> tuple[MutationReceipt, ...]:
        async with DataHubMCPProvider(config) as provider:
            return await execute_writeback_proposals(
                provider,
                evidence.writeback_proposals,
                run_id=evidence.run_id,
                approval_granted=True,
            )

    receipts = asyncio.run(retry())
    payload = [receipt.model_dump(mode="json") for receipt in receipts]
    if any(item["status"] != "skipped_idempotent_verified" for item in payload):
        raise RuntimeError("Retry verification observed a non-idempotent mutation.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    console.print(JSON.from_data(payload))


if __name__ == "__main__":
    app()
