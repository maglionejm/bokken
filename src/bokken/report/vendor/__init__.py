"""Vendored third-party assets inlined into generated reports.

chart.umd.min.js is Chart.js v4.4.7 (MIT, (c) Chart.js contributors,
https://www.chartjs.org) - vendored so report.html is fully self-contained
and opens offline. See NOTICE.
"""

from pathlib import Path


def chartjs_source() -> str:
    return (Path(__file__).parent / "chart.umd.min.js").read_text(encoding="utf-8")
