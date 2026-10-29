import pandas as pd

from netbench.report import build_report, latest_period

COLUMNS = [
    "country_code",
    "year",
    "quarter",
    "avg_download_mbps",
    "avg_upload_mbps",
    "avg_latency_ms",
    "tests",
    "download_rank",
    "latency_rank",
]


def _kpis() -> pd.DataFrame:
    rows = [
        ("HU", 2026, 2, 60.0, 15.0, 30.0, 100, 2, 2),
        ("PL", 2026, 2, 70.0, 16.0, 28.0, 200, 1, 1),
        ("HU", 2026, 3, 80.0, 17.0, 25.0, 120, 1, 1),
        ("PL", 2026, 3, 75.0, 18.0, 27.0, 210, 2, 2),
    ]
    return pd.DataFrame(rows, columns=COLUMNS)


def test_latest_period_keeps_only_last_quarter() -> None:
    assert set(latest_period(_kpis())["quarter"]) == {3}


def test_report_contains_charts_ranking_and_attribution() -> None:
    html = build_report(_kpis())
    assert "Hungary" in html
    assert "Ranking, 2026-Q3" in html
    assert "plotly" in html.lower()
    assert "Speedtest" in html
