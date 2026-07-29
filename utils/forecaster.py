"""
forecaster.py
-------------
Simple next-month expense forecasting for FinSight.

Takes the output of analyzer.monthly_summary() (a DataFrame with columns
month, income, expense, net) and produces a forecast for the next month
using two methods:

    - rolling_average_forecast()  -> average of the last N months' expense
    - linear_trend_forecast()     -> straight-line trend projected forward

forecast_next_month() returns both estimates together, and
forecast_chart_df() returns a DataFrame ready to plot actual vs forecast
on the same line chart.

This module has no dependency on cleaner.py or raw transaction data —
it only operates on the already-aggregated monthly summary, so it can
be tested independently.
"""

import numpy as np
import pandas as pd


def _next_month_label(last_month_str):
    """Given a display month string like 'Jul 2026', return the next
    month in the same format, e.g. 'Aug 2026'."""
    dt = pd.to_datetime(last_month_str, format="%b %Y")
    next_dt = dt + pd.DateOffset(months=1)
    return next_dt.strftime("%b %Y")


def rolling_average_forecast(summary_df, window=3):
    """Forecast next month's expense as the average of the last `window`
    months. If fewer months exist than `window`, uses all available months."""
    if summary_df.empty:
        return 0.0
    window = min(window, len(summary_df))
    return round(summary_df["expense"].tail(window).mean(), 2)


def linear_trend_forecast(summary_df):
    """Forecast next month's expense by fitting a straight line (least
    squares) through all months and projecting one step forward.

    Falls back to a plain average when there are fewer than 2 months of
    data (a line can't be fit through a single point). Negative
    forecasts are clipped to 0, since expenses can't be negative.
    """
    if len(summary_df) < 2:
        return rolling_average_forecast(summary_df, window=1)

    y = summary_df["expense"].values
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)

    next_x = len(y)
    forecast = slope * next_x + intercept
    return round(max(forecast, 0.0), 2)


def forecast_next_month(summary_df, window=3):
    """Return both forecast estimates for the month after the last one
    in summary_df, as a dict:
        {"month": "Aug 2026", "rolling_avg_estimate": ..., "trend_estimate": ...}
    """
    if summary_df.empty:
        return {"month": None, "rolling_avg_estimate": 0.0, "trend_estimate": 0.0}

    next_month = _next_month_label(summary_df.iloc[-1]["month"])
    return {
        "month": next_month,
        "rolling_avg_estimate": rolling_average_forecast(summary_df, window=window),
        "trend_estimate": linear_trend_forecast(summary_df),
    }


def forecast_next_n_months(summary_df, n=3, window=3):
    """Forecast the next `n` months' expense, returned as a DataFrame with
    columns: month, rolling_avg_estimate, trend_estimate.

    Rolling average is projected iteratively — each forecasted month is
    appended to a working series so the next month's rolling average is
    computed over actuals + prior forecasts, the same way you'd naturally
    keep rolling a 3-month average forward.

    Linear trend is projected directly from the original fit (slope/intercept
    fit once on the actual data), evaluated at x = len, len+1, len+2, ...
    — this avoids the trend line bending under the influence of its own
    forecasted points.
    """
    if summary_df.empty:
        return pd.DataFrame(columns=["month", "rolling_avg_estimate", "trend_estimate"])

    # --- Trend: fit once on actual data, then project forward n steps ---
    y = summary_df["expense"].values
    if len(y) >= 2:
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        trend_estimates = [round(max(slope * (len(y) + i) + intercept, 0.0), 2) for i in range(n)]
    else:
        flat = rolling_average_forecast(summary_df, window=1)
        trend_estimates = [flat] * n

    # --- Rolling average: project iteratively, feeding forecasts back in ---
    rolling_series = list(summary_df["expense"].values)
    rolling_estimates = []
    for _ in range(n):
        w = min(window, len(rolling_series))
        next_val = round(sum(rolling_series[-w:]) / w, 2)
        rolling_estimates.append(next_val)
        rolling_series.append(next_val)

    # --- Month labels ---
    last_month = summary_df.iloc[-1]["month"]
    months = []
    cursor = last_month
    for _ in range(n):
        cursor = _next_month_label(cursor)
        months.append(cursor)

    return pd.DataFrame(
        {
            "month": months,
            "rolling_avg_estimate": rolling_estimates,
            "trend_estimate": trend_estimates,
        }
    )


def forecast_chart_df(summary_df, window=3, method="rolling", n=1):
    """Return a DataFrame combining actual monthly expenses with `n`
    forecasted future rows, tagged by a 'type' column ('actual' /
    'forecast') — ready to feed into a Plotly line chart colored by type.

    `method` picks which estimate becomes the plotted forecast point:
    "rolling" (default) or "trend". `n=1` (default) reproduces the old
    single-month-ahead behavior; pass n=3 for a 3-month-ahead chart.
    """
    forecast_df = forecast_next_n_months(summary_df, n=n, window=window)
    chart_df = summary_df[["month", "expense"]].copy()
    chart_df["type"] = "actual"

    if not forecast_df.empty:
        col = "rolling_avg_estimate" if method == "rolling" else "trend_estimate"
        future_rows = forecast_df[["month", col]].rename(columns={col: "expense"})
        future_rows["type"] = "forecast"
        chart_df = pd.concat([chart_df, future_rows], ignore_index=True)

    return chart_df


# ---------------------------------------------------------------------------
# Manual test when run directly: `python utils/forecaster.py`
# ---------------------------------------------------------------------------

def main():
    from pathlib import Path
    from cleaner import load_categories, clean_transactions
    from analyzer import monthly_summary

    BASE = Path(__file__).resolve().parent.parent
    raw = pd.read_csv(BASE / "data" / "sample_transactions.csv")
    categories = load_categories(BASE / "categories.json")
    df = clean_transactions(raw, categories)

    summary = monthly_summary(df)
    print("=== Monthly Summary ===")
    print(summary)

    print("\n=== Next Month Forecast ===")
    print(forecast_next_month(summary))

    print("\n=== Next 3 Months Forecast ===")
    print(forecast_next_n_months(summary, n=3))

    print("\n=== Chart-ready DataFrame (3 months) ===")
    print(forecast_chart_df(summary, n=3))

if __name__ == "__main__":
    main()