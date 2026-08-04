"""Deliberately unsafe baseline DAG used by the EvidenceGraph demo."""

from datetime import UTC, datetime

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="daily_customer_value",
    start_date=datetime(2026, 8, 1, tzinfo=UTC),
    schedule="0 4 * * *",
    catchup=False,
) as dag:
    publish_customer_value = BashOperator(
        task_id="publish_customer_value",
        bash_command="dbt build --select +fct_customer_value",
    )
