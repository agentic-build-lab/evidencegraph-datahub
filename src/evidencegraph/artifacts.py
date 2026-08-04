"""Generate PR-ready migration artifacts from evidenced context."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from difflib import unified_diff
from textwrap import dedent

import yaml

from evidencegraph.models import (
    AssetKind,
    ChangeKind,
    ChangeRequest,
    ContextSnapshot,
    EvidenceClaim,
    GeneratedArtifact,
    Impact,
    MigrationStep,
    SchemaField,
)


class ArtifactGenerationError(RuntimeError):
    """Raised when evidence is insufficient to create a safe migration artifact."""


class ArtifactGenerator:
    """Produce deterministic artifacts; language models cannot bypass this boundary."""

    def generate(
        self,
        change: ChangeRequest,
        snapshot: ContextSnapshot,
        impacts: tuple[Impact, ...],
        claims: tuple[EvidenceClaim, ...],
        plan: tuple[MigrationStep, ...],
    ) -> tuple[GeneratedArtifact, ...]:
        if change.kind != ChangeKind.DROP_COLUMN or change.field != "customer_tier":
            raise ArtifactGenerationError(
                "The deterministic generator has no evidence-tested strategy for this change."
            )
        source = snapshot.asset_map().get(change.asset_urn)
        if source is None:
            raise ArtifactGenerationError("The changed DataHub asset is absent from context.")
        migration_document = next(
            (
                document
                for document in snapshot.documents
                if document.facts.get("field") == change.field
                and document.facts.get("replacement_field")
                and change.asset_urn in document.related_urns
                and document.facts.get("approved_by") in source.owners
            ),
            None,
        )
        if migration_document is None:
            raise ArtifactGenerationError(
                "No approved DataHub migration document provides a replacement mapping."
            )
        replacement, mapping = self._validated_migration_facts(
            migration_document.facts, source.schema_fields
        )
        claim_ids = tuple(claim.claim_id for claim in claims if claim.subject_urn)
        target_urns = tuple(impact.asset_urn for impact in impacts)

        artifacts = [
            self._artifact(
                "migration/sql/customer_tier_compatibility.sql",
                "sql",
                "Preserve the contracted field from the documented replacement mapping.",
                self._compatibility_sql(change.field, replacement, mapping),
                target_urns,
                claim_ids,
            ),
            self._artifact(
                "migration/dbt/models/staging/stg_orders.sql",
                "dbt-sql",
                "Update the staging model while keeping the downstream contract stable.",
                self._dbt_model(change.field, replacement, mapping),
                target_urns,
                claim_ids,
            ),
            self._artifact(
                "migration/patches/demo-platform.patch",
                "unified-diff",
                "Apply the evidenced dbt compatibility change to the miniature platform.",
                self._dbt_patch(change.field, replacement, mapping),
                target_urns,
                claim_ids,
            ),
            self._artifact(
                "migration/dbt/models/staging/stg_orders.yml",
                "dbt-yaml",
                "Encode the compatibility field contract and accepted values.",
                self._dbt_schema(),
                target_urns,
                claim_ids,
            ),
            self._artifact(
                "migration/validation/validate_customer_tier.sql",
                "validation-sql",
                "Reject unmapped segment codes and prove parity with the current field.",
                self._validation_sql(),
                target_urns,
                claim_ids,
            ),
            self._artifact(
                "migration/MIGRATION_PLAN.md",
                "markdown",
                "Give reviewers an evidence-linked, ordered migration plan.",
                self._migration_markdown(change, impacts, plan),
                target_urns,
                claim_ids,
            ),
        ]
        if any(impact.kind in {AssetKind.DATA_JOB, AssetKind.PIPELINE} for impact in impacts):
            artifacts.append(
                self._artifact(
                    "migration/orchestration/evidencegraph_change_gate.py",
                    "airflow-python",
                    "Add an Airflow pre-publish gate that fails closed on validation errors.",
                    self._airflow_gate(),
                    tuple(
                        impact.asset_urn
                        for impact in impacts
                        if impact.kind in {AssetKind.DATA_JOB, AssetKind.PIPELINE}
                    ),
                    claim_ids,
                )
            )
        if any(
            impact.kind
            in {
                AssetKind.ML_FEATURE,
                AssetKind.ML_FEATURE_TABLE,
                AssetKind.ML_MODEL,
                AssetKind.ML_MODEL_DEPLOYMENT,
            }
            for impact in impacts
        ):
            artifacts.append(
                self._artifact(
                    "migration/ml/customer_tier_feature_v2.yml",
                    "ml-feature-contract",
                    "Version the ML feature and require parity before deployment.",
                    self._ml_contract(mapping),
                    tuple(
                        impact.asset_urn
                        for impact in impacts
                        if impact.kind
                        in {
                            AssetKind.ML_FEATURE,
                            AssetKind.ML_FEATURE_TABLE,
                            AssetKind.ML_MODEL,
                            AssetKind.ML_MODEL_DEPLOYMENT,
                        }
                    ),
                    claim_ids,
                )
            )
        manifest_content = json.dumps(
            {
                "change_id": change.change_id,
                "source_document": migration_document.urn,
                "artifacts": [artifact.relative_path for artifact in artifacts],
                "target_urns": list(target_urns),
                "evidence_claim_ids": list(claim_ids),
            },
            indent=2,
            sort_keys=True,
        )
        artifacts.append(
            self._artifact(
                "migration/evidencegraph-manifest.json",
                "manifest",
                "Bind every generated file to its DataHub evidence and affected assets.",
                manifest_content + "\n",
                target_urns,
                claim_ids,
            )
        )
        return tuple(artifacts)

    @staticmethod
    def _validated_migration_facts(
        facts: Mapping[str, object], schema_fields: Sequence[SchemaField]
    ) -> tuple[str, dict[str, str]]:
        replacement = facts.get("replacement_field")
        if not isinstance(replacement, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", replacement
        ):
            raise ArtifactGenerationError("The replacement field is not a safe SQL identifier.")
        observed_names = {
            getattr(field, "name", None)
            for field in schema_fields
            if isinstance(getattr(field, "name", None), str)
        }
        if replacement not in observed_names:
            raise ArtifactGenerationError(
                "The replacement field is absent from the observed producer schema."
            )
        raw_mapping = facts.get("mapping")
        expected_mapping = {"B": "bronze", "S": "silver", "G": "gold"}
        if raw_mapping != expected_mapping:
            raise ArtifactGenerationError(
                "The migration mapping is not the evidence-tested B/S/G contract."
            )
        if facts.get("unknown_policy") != "reject":
            raise ArtifactGenerationError("Unknown replacement values must fail closed.")
        mapping = {
            key: value
            for key, value in expected_mapping.items()
            if re.fullmatch(r"[A-Za-z0-9_-]+", key) and re.fullmatch(r"[A-Za-z0-9_-]+", value)
        }
        if mapping != expected_mapping:
            raise ArtifactGenerationError("The migration mapping contains unsafe literals.")
        return replacement, mapping

    @staticmethod
    def _artifact(
        relative_path: str,
        kind: str,
        purpose: str,
        content: str,
        target_urns: tuple[str, ...],
        claim_ids: tuple[str, ...],
    ) -> GeneratedArtifact:
        return GeneratedArtifact(
            relative_path=relative_path,
            kind=kind,
            purpose=purpose,
            content=content,
            sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            target_urns=target_urns,
            evidence_claim_ids=claim_ids,
        )

    @staticmethod
    def _case_expression(replacement: str, mapping: Mapping[str, str]) -> str:
        branches = "\n".join(
            f"        WHEN '{key}' THEN '{value}'" for key, value in sorted(mapping.items())
        )
        return f"CASE {replacement}\n{branches}\n        ELSE NULL\n    END"

    def _compatibility_sql(self, field: str, replacement: str, mapping: Mapping[str, str]) -> str:
        expression = self._case_expression(replacement, mapping)
        # field, replacement, and mapping have already passed the closed identifier
        # and value allowlists before this deterministic template is rendered.
        return dedent(
            f"""
            -- EvidenceGraph change EG-042. Source: DataHub document RFC-42.
            CREATE OR REPLACE VIEW stg_orders_compat AS
            SELECT
                order_id,
                customer_id,
                amount_usd,
                {expression} AS {field},
                ordered_at
            FROM raw_orders_next;
            """  # nosec B608
        ).lstrip()

    def _dbt_model(self, field: str, replacement: str, mapping: Mapping[str, str]) -> str:
        expression = self._case_expression(replacement, mapping)
        # This is a generated dbt artifact, not a query executed against user input;
        # every interpolated token is validated against the proposal contract first.
        return dedent(
            f"""
            {{{{ config(materialized='view', contract={{'enforced': true}}) }}}}
            -- Evidence claims are enumerated in migration/evidencegraph-manifest.json.
            SELECT
                order_id,
                customer_id,
                amount_usd,
                {expression} AS {field},
                ordered_at
            FROM {{{{ source('commerce', 'raw_orders_next') }}}}
            """  # nosec B608
        ).lstrip()

    def _dbt_patch(self, field: str, replacement: str, mapping: Mapping[str, str]) -> str:
        before = dedent(
            """
            {{ config(materialized='view', contract={'enforced': true}) }}
            SELECT
                order_id,
                customer_id,
                amount_usd,
                customer_tier,
                ordered_at
            FROM {{ source('commerce', 'raw_orders_current') }}
            """
        ).lstrip()
        after = self._dbt_model(field, replacement, mapping)
        return "".join(
            unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile="a/demo_platform/dbt/models/staging/stg_orders.sql",
                tofile="b/demo_platform/dbt/models/staging/stg_orders.sql",
            )
        )

    @staticmethod
    def _dbt_schema() -> str:
        payload = {
            "version": 2,
            "models": [
                {
                    "name": "stg_orders",
                    "description": "Compatibility model generated from DataHub RFC-42.",
                    "config": {"contract": {"enforced": True}},
                    "columns": [
                        {
                            "name": "order_id",
                            "data_type": "bigint",
                            "data_tests": ["not_null", "unique"],
                        },
                        {"name": "customer_id", "data_type": "bigint", "data_tests": ["not_null"]},
                        {
                            "name": "amount_usd",
                            "data_type": "decimal(12,2)",
                            "data_tests": ["not_null"],
                        },
                        {
                            "name": "customer_tier",
                            "data_type": "varchar",
                            "data_tests": [
                                "not_null",
                                {
                                    "accepted_values": {
                                        "arguments": {"values": ["bronze", "silver", "gold"]}
                                    }
                                },
                            ],
                        },
                        {
                            "name": "ordered_at",
                            "data_type": "timestamp",
                            "data_tests": ["not_null"],
                        },
                    ],
                    "meta": {"evidencegraph_change": "EG-042"},
                }
            ],
        }
        return yaml.safe_dump(payload, sort_keys=False)

    @staticmethod
    def _validation_sql() -> str:
        return dedent(
            """
            -- Native DuckDB validation. Zero rows is the only passing result.
            SELECT
                n.order_id,
                n.segment_code,
                c.customer_tier AS expected,
                s.customer_tier AS actual
            FROM raw_orders_next AS n
            LEFT JOIN raw_orders_current AS c USING (order_id)
            LEFT JOIN stg_orders_compat AS s USING (order_id)
            WHERE s.customer_tier IS NULL
               OR s.customer_tier NOT IN ('bronze', 'silver', 'gold')
               OR s.customer_tier <> c.customer_tier;
            """
        ).lstrip()

    @staticmethod
    def _airflow_gate() -> str:
        return dedent(
            '''
            """Airflow snippet generated for EvidenceGraph change EG-042."""

            import json
            import os
            import re
            from datetime import UTC, datetime
            from pathlib import Path

            from airflow import DAG
            from airflow.providers.standard.operators.bash import BashOperator
            from airflow.providers.standard.operators.python import PythonOperator


            def require_validated_evidence() -> str:
                expected_validation_ids = {
                    "VAL-INTEGRITY",
                    "VAL-PARSE-01",
                    "VAL-PARSE-02",
                    "VAL-PARSE-03",
                    "VAL-PARSE-04",
                    "VAL-PARSE-05",
                    "VAL-PARSE-06",
                    "VAL-PARSE-07",
                    "VAL-PARSE-08",
                    "VAL-PATCH-APPLY",
                    "VAL-DUCKDB-PARITY",
                    "VAL-DBT-BUILD",
                    "VAL-AIRFLOW-DAG",
                    "VAL-ML-PARITY",
                }
                ledger_path = Path(
                    os.environ.get(
                        "EVIDENCEGRAPH_LEDGER_PATH",
                        "/opt/evidencegraph/evidence-ledger.json",
                    )
                )
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                validations = ledger.get("validations", [])
                validation_ids = [item.get("validation_id") for item in validations]
                failed = [
                    item.get("validation_id", "unknown")
                    for item in validations
                    if item.get("status") != "passed"
                ]
                malformed_receipts = [
                    item.get("validation_id", "unknown")
                    for item in validations
                    if re.fullmatch(r"[0-9a-f]{64}", item.get("output_sha256", "")) is None
                ]
                input_sha256 = ledger.get("input_sha256", "")
                expected_run_id = f"EG-{input_sha256[:12].upper()}"
                identity_valid = (
                    ledger.get("change", {}).get("change_id") == "EG-042"
                    and re.fullmatch(r"[0-9a-f]{64}", input_sha256) is not None
                    and ledger.get("run_id") == expected_run_id
                )
                receipt_set_valid = (
                    len(validation_ids) == len(expected_validation_ids)
                    and set(validation_ids) == expected_validation_ids
                )
                if failed or malformed_receipts or not identity_valid or not receipt_set_valid:
                    raise RuntimeError(
                        "EvidenceGraph validation gate rejected the bundle: "
                        f"failed={failed}, malformed={malformed_receipts}, "
                        f"identity_valid={identity_valid}, receipt_set_valid={receipt_set_valid}"
                    )
                return expected_run_id


            with DAG(
                dag_id="daily_customer_value_migration",
                start_date=datetime(2026, 8, 1, tzinfo=UTC),
                schedule="0 4 * * *",
                catchup=False,
                tags=["evidencegraph", "EG-042"],
            ) as dag:
                validate_change = PythonOperator(
                    task_id="validate_customer_tier_compatibility",
                    python_callable=require_validated_evidence,
                )

                publish_customer_value = BashOperator(
                    task_id="publish_customer_value",
                    bash_command="dbt build --select +fct_customer_value",
                )

                validate_change >> publish_customer_value
            '''
        ).lstrip()

    @staticmethod
    def _ml_contract(mapping: Mapping[str, str]) -> str:
        payload = {
            "apiVersion": "evidencegraph.io/v1",
            "kind": "MLFeatureMigration",
            "metadata": {"name": "customer-tier-signal-v2", "changeId": "EG-042"},
            "spec": {
                "sourceField": "segment_code",
                "outputFeature": "customer_tier_signal_v2",
                "mapping": mapping,
                "unknownValuePolicy": "reject",
                "parity": {"required": True, "minimumRows": 4, "maximumMismatchRate": 0.0},
                "deploymentGate": {
                    "modelUrn": (
                        "urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn_propensity_v4,PROD)"
                    ),
                    "deploymentUrn": (
                        "urn:li:mlModelDeployment:(urn:li:dataPlatform:kubernetes,"
                        "churn_api_prod,PROD)"
                    ),
                },
            },
        }
        return yaml.safe_dump(payload, sort_keys=False)

    @staticmethod
    def _migration_markdown(
        change: ChangeRequest,
        impacts: tuple[Impact, ...],
        plan: tuple[MigrationStep, ...],
    ) -> str:
        lines = [
            f"# Migration plan for {change.change_id}",
            "",
            f"Proposed change: `{change.kind.value}` on `{change.asset_urn}` / `{change.field}`.",
            "",
            "## Risk-ranked consumers",
            "",
            "| Risk | Score | Asset | Owner | Evidence path count |",
            "|---|---:|---|---|---:|",
        ]
        for impact in impacts:
            lines.append(
                f"| {impact.risk_level.value} | {impact.risk_score} | `{impact.asset_urn}` | "
                f"{', '.join(impact.owners) or 'UNOWNED'} | {len(impact.paths)} |"
            )
        lines.extend(["", "## Ordered steps", ""])
        for step in plan:
            gate = "BLOCKING" if step.blocking else "non-blocking"
            lines.append(f"{step.order}. **{step.title}** ({gate}) — {step.action}")
        lines.extend(
            [
                "",
                "## Merge policy",
                "",
                "Do not merge until every generated validation is `passed`, the DataHub "
                "context frontier is complete, and the fresh-graph closure check finds no "
                "unremediated consumer.",
                "",
            ]
        )
        return "\n".join(lines)
