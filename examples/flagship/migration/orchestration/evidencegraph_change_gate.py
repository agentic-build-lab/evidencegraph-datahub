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
