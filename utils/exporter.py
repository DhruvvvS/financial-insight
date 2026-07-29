"""
exporter.py
-----------
PDF report generation for FinSight, using fpdf2.

generate_pdf_report() builds a one-page summary PDF (KPIs, monthly
summary table, top categories table) and returns it as raw bytes,
ready to hand straight to st.download_button(data=...).

Excel export doesn't need a dedicated module — pandas.ExcelWriter
(with the openpyxl engine) handles that directly in app.py.
"""

from fpdf import FPDF, XPos, YPos


class _Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "FinSight - Financial Summary Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_font("Helvetica", size=9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, self._subtitle if hasattr(self, "_subtitle") else "", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _section_title(pdf, text):
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=11)


def _table_row(pdf, values, widths, border=1, bold=False):
    pdf.set_font("Helvetica", "B" if bold else "", 10)
    for value, width in zip(values, widths):
        pdf.cell(width, 7, str(value), border=border)
    pdf.ln()


def generate_pdf_report(kpi_dict, summary_df, breakdown_df, source_name="transactions.csv", forecast_df=None):
    """Build the PDF report and return it as bytes.

    Parameters mirror what app.py already has on hand:
        kpi_dict     -> output of analyzer.kpi(df)
        summary_df   -> output of analyzer.monthly_summary(df)
        breakdown_df -> output of analyzer.category_breakdown(df)
        source_name  -> filename or label to show as the data source
        forecast_df  -> optional, output of forecaster.forecast_next_n_months(df).
                         When provided, adds a "Next Months Forecast" section.
                         Omit (default None) to skip the forecast section entirely.
    """
    pdf = _Report()
    pdf._subtitle = f"Data source: {source_name}"
    pdf.add_page()

    # --- Key metrics ---
    _section_title(pdf, "Key Metrics")
    pdf.cell(0, 7, f"Total Income:   Rs {kpi_dict['total_income']:,.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Total Expense:  Rs {kpi_dict['total_expense']:,.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Net:            Rs {kpi_dict['net']:,.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Savings Rate:   {kpi_dict['savings_rate_pct']:.1f}%", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Top Category:   {str(kpi_dict['top_category']).replace('_', ' ').title()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # --- Monthly summary table ---
    _section_title(pdf, "Monthly Summary")
    col_widths = [40, 45, 45, 45]
    _table_row(pdf, ["Month", "Income (Rs)", "Expense (Rs)", "Net (Rs)"], col_widths, bold=True)
    for _, row in summary_df.iterrows():
        _table_row(
            pdf,
            [row["month"], f"{row['income']:,.0f}", f"{row['expense']:,.0f}", f"{row['net']:,.0f}"],
            col_widths,
        )
    pdf.ln(4)

    # --- Top categories table ---
    _section_title(pdf, "Top Categories")
    col_widths2 = [90, 45]
    _table_row(pdf, ["Category", "Total Spend (Rs)"], col_widths2, bold=True)
    for _, row in breakdown_df.head(10).iterrows():
        _table_row(
            pdf,
            [str(row["category"]).replace("_", " ").title(), f"{row['total_spend']:,.0f}"],
            col_widths2,
        )

    # --- Forecast table (optional) ---
    if forecast_df is not None and not forecast_df.empty:
        pdf.ln(4)
        n_months = len(forecast_df)
        _section_title(pdf, f"Next {n_months} Months Forecast")
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(
            0, 6,
            "Rolling Avg = average of recent months. Trend = straight-line projection.",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        pdf.set_font("Helvetica", size=11)
        col_widths3 = [50, 60, 60]
        _table_row(pdf, ["Month", "Rolling Avg (Rs)", "Trend (Rs)"], col_widths3, bold=True)
        for _, row in forecast_df.iterrows():
            _table_row(
                pdf,
                [
                    row["month"],
                    f"{row['rolling_avg_estimate']:,.0f}",
                    f"{row['trend_estimate']:,.0f}",
                ],
                col_widths3,
            )

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# Manual test when run directly: `python utils/exporter.py`
# ---------------------------------------------------------------------------

def main():
    from pathlib import Path
    import pandas as pd
    from cleaner import load_categories, clean_transactions
    from analyzer import monthly_summary, category_breakdown, kpi
    from forecaster import forecast_next_n_months

    BASE = Path(__file__).resolve().parent.parent
    raw = pd.read_csv(BASE / "data" / "sample_transactions.csv")
    categories = load_categories(BASE / "categories.json")
    df = clean_transactions(raw, categories)

    summary = monthly_summary(df)

    pdf_bytes = generate_pdf_report(
        kpi_dict=kpi(df),
        summary_df=summary,
        breakdown_df=category_breakdown(df),
        source_name="sample_transactions.csv",
        forecast_df=forecast_next_n_months(summary, n=3),
    )

    out_path = BASE / "finsight_report_test.pdf"
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"Wrote {len(pdf_bytes)} bytes to {out_path}")

if __name__ == "__main__":
    main()