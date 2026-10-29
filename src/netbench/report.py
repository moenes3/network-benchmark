"""Analytics -> reports: an interactive Plotly benchmark report (one HTML file)."""

import logging
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pyarrow.parquet as pq

from netbench.aggregate import KPIS_PREFIX
from netbench.config import Settings, load_settings
from netbench.logging_setup import setup_logging
from netbench.storage import ensure_bucket, make_arrow_filesystem, make_s3_client

logger = logging.getLogger(__name__)

REPORT_KEY = "benchmark_report.html"
LOCAL_REPORT = Path("data/reports") / REPORT_KEY

HIGHLIGHT = "HU"
ACCENT = "#2a78d6"
NEUTRAL = "#b7b6b1"
INK = "#0b0b0b"
MUTED = "#52514e"

COUNTRY_NAMES = {
    "HU": "Hungary",
    "PL": "Poland",
    "CZ": "Czechia",
    "SK": "Slovakia",
    "RO": "Romania",
    "BG": "Bulgaria",
    "SI": "Slovenia",
    "HR": "Croatia",
    "EE": "Estonia",
    "LV": "Latvia",
    "LT": "Lithuania",
}

LAYOUT = {
    "template": "plotly_white",
    "font": {"family": "Inter, Helvetica, Arial, sans-serif", "color": INK, "size": 13},
    "margin": {"l": 110, "r": 70, "t": 60, "b": 50},
    "height": 440,
    "showlegend": False,
}


def add_labels(kpis: pd.DataFrame) -> pd.DataFrame:
    labelled = kpis.copy()
    codes = labelled["country_code"]
    labelled["country"] = codes.map(COUNTRY_NAMES).fillna(codes)
    labelled["period"] = labelled["year"].astype(str) + "-Q" + labelled["quarter"].astype(str)
    return labelled.sort_values(["year", "quarter"])


def latest_period(kpis: pd.DataFrame) -> pd.DataFrame:
    last = kpis[["year", "quarter"]].drop_duplicates().sort_values(["year", "quarter"]).iloc[-1]
    return kpis[(kpis["year"] == last["year"]) & (kpis["quarter"] == last["quarter"])]


def _colors(codes: pd.Series) -> list[str]:
    return [ACCENT if code == HIGHLIGHT else NEUTRAL for code in codes]


def ranking_bar(latest: pd.DataFrame, column: str, unit: str, title: str) -> go.Figure:
    ascending = column != "avg_latency_ms"  # bars sorted so the best country is on top
    data = latest.sort_values(column, ascending=ascending)
    figure = go.Figure(
        go.Bar(
            x=data[column],
            y=data["country"],
            orientation="h",
            marker={"color": _colors(data["country_code"])},
            text=data[column].map("{:.2f}".format),
            textposition="outside",
            textfont={"color": INK},
            hovertemplate=f"%{{y}}: %{{x:.2f}} {unit}<extra></extra>",
        )
    )
    figure.update_layout(title=title, xaxis_title=unit, **LAYOUT)
    return figure


def trend_lines(kpis: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    # Grey lines first, the highlighted country last so it is drawn on top.
    for code in sorted(kpis["country_code"].unique(), key=lambda c: c == HIGHLIGHT):
        series = kpis[kpis["country_code"] == code]
        is_highlight = code == HIGHLIGHT
        labels = [""] * (len(series) - 1) + [series["country"].iloc[-1]]
        figure.add_trace(
            go.Scatter(
                x=series["period"],
                y=series["avg_download_mbps"],
                mode="lines+markers+text",
                text=labels,
                textposition="middle right",
                textfont={"color": INK if is_highlight else MUTED},
                line={
                    "color": ACCENT if is_highlight else NEUTRAL,
                    "width": 3 if is_highlight else 2,
                },
                marker={"size": 8},
                name=series["country"].iloc[-1],
                hovertemplate="%{fullData.name} %{x}: %{y:.2f} Mbps<extra></extra>",
            )
        )
    figure.update_layout(title="Average download speed per quarter", yaxis_title="Mbps", **LAYOUT)
    return figure


def build_report(kpis: pd.DataFrame) -> str:
    """Return the full HTML report for a KPI table (one row per country and quarter)."""
    labelled = add_labels(kpis)
    latest = latest_period(labelled)
    period = latest["period"].iloc[0]

    figures = [
        ranking_bar(latest, "avg_download_mbps", "Mbps", f"Average download speed, {period}"),
        trend_lines(labelled),
        ranking_bar(latest, "avg_upload_mbps", "Mbps", f"Average upload speed, {period}"),
        ranking_bar(latest, "avg_latency_ms", "ms", f"Average latency, {period} (lower is better)"),
    ]
    charts = "\n".join(
        figure.to_html(full_html=False, include_plotlyjs="cdn" if index == 0 else False)
        for index, figure in enumerate(figures)
    )
    table_columns = [
        "download_rank",
        "country",
        "avg_download_mbps",
        "avg_upload_mbps",
        "avg_latency_ms",
        "tests",
    ]
    table = (
        latest.sort_values("download_rank")[table_columns]
        .rename(columns=lambda name: name.replace("_", " "))
        .to_html(index=False, float_format="{:.2f}".format, classes="kpis", border=0)
    )
    periods = f"{labelled['period'].iloc[0]} to {period}"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mobile Network Benchmark</title>
<style>
  body {{ font-family: Inter, Helvetica, Arial, sans-serif; color: {INK}; background: #fcfcfb;
         max-width: 980px; margin: 0 auto; padding: 24px 16px; }}
  h1 {{ font-size: 24px; margin-bottom: 4px; }}
  p.meta {{ color: {MUTED}; margin-top: 0; }}
  table.kpis {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
  table.kpis th, table.kpis td {{ padding: 6px 10px; text-align: right;
                                  border-bottom: 1px solid #e4e3df; }}
  table.kpis th:nth-child(2), table.kpis td:nth-child(2) {{ text-align: left; }}
  footer {{ color: {MUTED}; font-size: 12px; margin-top: 24px; }}
</style></head><body>
<h1>Mobile network performance: Central and Eastern Europe</h1>
<p class="meta">Test-weighted averages per country, {periods}. Hungary highlighted.</p>
{charts}
<h2>Ranking, {period}</h2>
{table}
<footer>Speedtest&reg; by Ookla&reg; Global Fixed and Mobile Network Performance Maps.
Based on analysis by Ookla of Speedtest Intelligence&reg; data for {periods}.
Provided by Ookla. Ookla trademarks used under license and reprinted with permission.</footer>
</body></html>
"""


def load_kpis(settings: Settings) -> pd.DataFrame:
    path = f"{settings.analytics_bucket}/{KPIS_PREFIX}"
    return pq.read_table(path, filesystem=make_arrow_filesystem(settings)).to_pandas()


def run(settings: Settings) -> None:
    html = build_report(load_kpis(settings))

    LOCAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_REPORT.write_text(html, encoding="utf-8")

    client = make_s3_client(settings)
    ensure_bucket(client, settings.reports_bucket)
    client.put_object(
        Bucket=settings.reports_bucket,
        Key=REPORT_KEY,
        Body=html.encode("utf-8"),
        ContentType="text/html",
    )
    logger.info(
        "Report saved to %s and s3://%s/%s", LOCAL_REPORT, settings.reports_bucket, REPORT_KEY
    )


def main() -> None:
    setup_logging()
    run(load_settings())


if __name__ == "__main__":
    main()
