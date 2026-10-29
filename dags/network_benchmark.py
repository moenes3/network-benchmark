"""Mobile network benchmark pipeline: ingest -> transform -> aggregate -> report.

The DAG file only wires tasks together. All logic lives in the netbench package and
each task runs one of its command-line entry points, so every step can also be run
(and tested) without Airflow.
"""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

QUARTERS = [(2025, 4), (2026, 1), (2026, 2), (2026, 3)]
PROJECT_DIR = "/opt/airflow"

with DAG(
    dag_id="network_benchmark",
    description="Benchmark mobile network performance in Central and Eastern Europe",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # triggered manually; "@quarterly" once new quarters are added automatically
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["netbench"],
) as dag:
    ensure_buckets = BashOperator(
        task_id="ensure_buckets",
        bash_command="python -m netbench.storage",
        cwd=PROJECT_DIR,
    )

    ingest_tasks = [
        BashOperator(
            task_id=f"ingest_{year}_q{quarter}",
            bash_command=f"python -m netbench.ingest --year {year} --quarter {quarter}",
            cwd=PROJECT_DIR,
        )
        for year, quarter in QUARTERS
    ]

    transform = BashOperator(
        task_id="transform",
        bash_command="python -m netbench.transform",
        cwd=PROJECT_DIR,
    )

    aggregate = BashOperator(
        task_id="aggregate",
        bash_command="python -m netbench.aggregate",
        cwd=PROJECT_DIR,
    )

    report = BashOperator(
        task_id="report",
        bash_command="python -m netbench.report",
        cwd=PROJECT_DIR,
    )

    ensure_buckets >> ingest_tasks >> transform >> aggregate >> report
