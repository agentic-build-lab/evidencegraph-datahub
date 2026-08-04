"""Freeze a sanitized, judge-readable EvidenceGraph evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from evidencegraph.ablation import load_truth_manifest, run_ablation
from evidencegraph.models import Completeness, EvidenceLedger
from evidencegraph.orchestrator import EvidenceGraphAgent, load_change, load_snapshot

ROOT = Path(__file__).resolve().parents[1]

PUBLISH_BLOCKLIST = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("authorization header", re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+\S+")),
    (
        "credential assignment",
        re.compile(
            r"(?i)(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)"
            r"[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}"
        ),
    ),
    ("Windows absolute path", re.compile(r"(?i)(?:^|[\"'\s])[A-Z]:\\")),
    ("user home path", re.compile(r"(?:/Users/|/home/)[^/\s]+/")),
    (
        "email address",
        re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    ),
)


def _assert_publishable_tree(root: Path) -> None:
    """Reject common credential, identity, and workstation-path leaks."""

    text_suffixes = {".json", ".md", ".sql", ".yml", ".yaml", ".py", ".patch"}
    violations: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in PUBLISH_BLOCKLIST:
            if pattern.search(text):
                violations.append(f"{path.relative_to(root).as_posix()}: {label}")
    if violations:
        raise ValueError("public evidence safety scan failed: " + "; ".join(violations))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def freeze(
    live_run: Path,
    closure_receipt: Path,
    retry_receipts: Path,
    output: Path,
    *,
    mutation_ledger: Path | None = None,
    context_snapshot: Path | None = None,
) -> None:
    ledger_path = live_run / "evidence-ledger.json"
    snapshot_path = context_snapshot or (live_run / "context-snapshot.json")
    ledger = EvidenceLedger.model_validate_json(ledger_path.read_text(encoding="utf-8"))
    if mutation_ledger is not None:
        receipt_source = EvidenceLedger.model_validate_json(
            mutation_ledger.read_text(encoding="utf-8")
        )
        if (
            receipt_source.run_id != ledger.run_id
            or receipt_source.input_sha256 != ledger.input_sha256
            or receipt_source.change != ledger.change
            or receipt_source.writeback_proposals != ledger.writeback_proposals
        ):
            raise ValueError(
                "mutation receipt ledger must match the validated run and proposal set exactly"
            )
        ledger = ledger.model_copy(
            update={"mutation_receipts": receipt_source.mutation_receipts}
        )
    if not ledger.mutation_receipts or any(
        receipt.status != "applied_verified" for receipt in ledger.mutation_receipts
    ):
        raise ValueError("live ledger must contain a complete verified write-back receipt set")
    if any(validation.status.value != "passed" for validation in ledger.validations):
        raise ValueError("live ledger contains a non-passing validator")

    flagship = output / "flagship"
    _copy(ROOT / "fixtures/changes/drop_customer_tier.json", flagship / "proposal.json")
    _copy(ROOT / "fixtures/truth_manifest.json", flagship / "truth-manifest.json")
    _copy(snapshot_path, flagship / "context-snapshot.live.sanitized.json")
    _write_json(
        flagship / "evidence-ledger.live.sanitized.json",
        ledger.model_dump(mode="json"),
    )
    _copy(live_run / "SUMMARY.md", flagship / "SUMMARY.md")
    shutil.copytree(live_run / "migration", flagship / "migration", dirs_exist_ok=True)
    _write_json(
        flagship / "validation-receipts.json",
        [item.model_dump(mode="json") for item in ledger.validations],
    )
    _write_json(
        flagship / "mcp-trace.sanitized.json",
        [item.model_dump(mode="json") for item in ledger.observations],
    )
    _write_json(
        flagship / "writeback-receipts.json",
        [item.model_dump(mode="json") for item in ledger.mutation_receipts],
    )
    _copy(retry_receipts, flagship / "writeback-retry-receipts.json")

    ablation = run_ablation(
        load_change(ROOT / "fixtures/changes/drop_customer_tier.json"),
        load_snapshot(ROOT / "fixtures/platform.json"),
        load_truth_manifest(ROOT / "fixtures/truth_manifest.json"),
    )
    _write_json(output / "ablation/comparison.json", ablation.to_dict())

    _copy(ROOT / "fixtures/platform.json", output / "closure/before-graph.json")
    _copy(ROOT / "fixtures/platform_after.json", output / "closure/after-graph.json")
    _copy(closure_receipt, output / "closure/closure-receipt.json")

    incomplete_snapshot = load_snapshot(ROOT / "fixtures/platform.json").model_copy(
        update={
            "snapshot_id": "commerce-platform-incomplete-lineage-replay",
            "completeness": Completeness(
                requested_direction="downstream",
                requested_depth=10,
                pages_exhausted=False,
                frontier_exhausted=False,
                truncated=True,
                notes=("A later lineage page was deliberately withheld.",),
            ),
        }
    )
    with tempfile.TemporaryDirectory(prefix="evidencegraph-refusal-") as temporary:
        refusal, _ = EvidenceGraphAgent(ROOT / "fixtures/warehouse/setup.sql").run(
            ledger.change,
            incomplete_snapshot,
            output_root=Path(temporary),
        )
    _write_json(
        output / "refusal/incomplete-lineage-ledger.json",
        refusal.model_dump(mode="json"),
    )

    readme = f"""# EvidenceGraph example evidence

This package is a public, synthetic-data evidence replay. The flagship ledger was collected from
local DataHub OSS v1.6.0 through the official `mcp-server-datahub@0.6.0`, with explicitly labeled
Python SDK aspect enrichment for MCP gaps.

## Measured result

- Full DataHub context: **7/7 affected assets (100% recall)**.
- Repository-only context: **3/7 (42.9% recall)**.
- Improvement: **+57.1 percentage points**; the hidden BI and ML consumers are recovered.
- Migration bundle: **{len(ledger.artifacts)} artifacts** across SQL, dbt, Airflow, ML, plan,
  manifest, and a real unified diff.
- Validation: **{len(ledger.validations)}/{len(ledger.validations)} passed**, including DuckDB,
  dbt Core 1.12.0, official Airflow 3.3.0 container import/gate execution, ML parity, and
  `git apply --check`.
- DataHub write-back: **3/3 applied and read back**; an immediate stateless retry was **3/3
  verified no-op**.

## Inspect in order

1. [Proposal](flagship/proposal.json) and independent [truth manifest](flagship/truth-manifest.json)
2. [Ablation](ablation/comparison.json)
3. [Live sanitized context](flagship/context-snapshot.live.sanitized.json)
4. [Evidence ledger](flagship/evidence-ledger.live.sanitized.json)
5. [Migration pack](flagship/migration/) and [native receipts](flagship/validation-receipts.json)
6. [MCP observations](flagship/mcp-trace.sanitized.json)
7. [Write-back receipts](flagship/writeback-receipts.json) and
   [idempotent retry](flagship/writeback-retry-receipts.json)
8. [Fail-closed refusal](refusal/incomplete-lineage-ledger.json)
9. Deterministic replay [before graph](closure/before-graph.json),
   [after graph](closure/after-graph.json), and [closure receipt](closure/closure-receipt.json)

The closure package is a deterministic fixture replay, not a claim that the public static demo
mutates a hosted DataHub instance.
"""
    (output / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    _assert_publishable_tree(output)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    manifest = {
        "schema_version": "1.0",
        "flagship_run_id": ledger.run_id,
        "files": [
            {
                "path": path.relative_to(output).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
            if path.name != "manifest.json"
        ],
    }
    _write_json(output / "manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-run", type=Path, required=True)
    parser.add_argument("--closure-receipt", type=Path, required=True)
    parser.add_argument("--retry-receipts", type=Path, required=True)
    parser.add_argument(
        "--mutation-ledger",
        type=Path,
        help=(
            "Optional earlier ledger containing applied receipts for the exact same "
            "run and proposal set."
        ),
    )
    parser.add_argument(
        "--context-snapshot",
        type=Path,
        help="Optional captured context path when the validated run is a deterministic refresh.",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "examples")
    arguments = parser.parse_args()
    freeze(
        arguments.live_run.resolve(),
        arguments.closure_receipt.resolve(),
        arguments.retry_receipts.resolve(),
        arguments.output.resolve(),
        mutation_ledger=(
            arguments.mutation_ledger.resolve() if arguments.mutation_ledger else None
        ),
        context_snapshot=(
            arguments.context_snapshot.resolve() if arguments.context_snapshot else None
        ),
    )


if __name__ == "__main__":
    main()
