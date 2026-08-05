"""
app.py
------
FinSight — Streamlit entry point.
 
Ties together:
    utils/cleaner.py   -> load_categories(), clean_transactions()
    utils/analyzer.py  -> monthly_summary(), category_breakdown(),
                           top_categories(), kpi()
 
Run with: streamlit run app.py
"""


# Imports
import io
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.cleaner import load_categories, clean_transactions
from utils.analyzer import monthly_summary, category_breakdown, top_categories, kpi
from utils.forecaster import forecast_next_month, forecast_chart_df, forecast_next_n_months
from utils.exporter import generate_pdf_report

# Constants
BASE = Path(__file__).resolve().parent

# -----------------------------
# Streamlit app
# -----------------------------
st.set_page_config(page_title="FinSight", page_icon="💸", layout="wide")

# Data Loading
def load_data(uploaded_file, categories):

    if uploaded_file is not None:
        raw = pd.read_csv(uploaded_file)
    else:
        raw = pd.read_csv(BASE/"data"/"sample_transactions.csv")

    return clean_transactions(raw, categories)

categories = load_categories(BASE / "categories.json")

# Sidebar: File upload and month filter
st.sidebar.title("💰 FinSight")
st.sidebar.caption("Personal & small-business finance analyzer")

uploaded_file = st.sidebar.file_uploader("Upload transactions CSV", type="csv")
use_sample = st.sidebar.checkbox("Use sample data", value=(uploaded_file is None))

# Load data into session state
if uploaded_file is not None:
    st.session_state["df"] = load_data(uploaded_file, categories)
    st.session_state["source"] = uploaded_file.name

elif use_sample and "df" not in st.session_state:
    st.session_state["df"] = load_data(None, categories)
    st.session_state["source"] = "sample_transactions.csv"

if "df" not in st.session_state:
    st.title("💰 FinSight")
    st.info("Upload a transactions CSV from the sidebar, or check **Use sample data** to explore with demo data.")
    st.stop()

# Main app logic
df = st.session_state["df"]
st.sidebar.success(f"Loaded: {st.session_state['source']} ({len(df)} transactions)")

# Sidebar: Month filter
month_options = ["All months"] + list(pd.Index(df["month"]).unique())
selected_month = st.sidebar.selectbox("Filter by month", month_options)
filter_month = None if selected_month == "All months" else selected_month

# Filter the DataFrame based on the selected month
view_df = df if filter_month is None else df[df["month"] == filter_month]

# Header and KPI
st.title("💸 FinSight")
st.caption("An end-to-end finance analyzer: upload → clean → categorize → visualize → export")
 
stats = kpi(view_df)
 
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Income", f"₹{stats['total_income']:,.0f}")
k2.metric("Total Expense", f"₹{stats['total_expense']:,.0f}")
k3.metric(
    "Net",
    f"₹{stats['net']:,.0f}",
    delta=f"{stats['savings_rate_pct']:.1f}% savings rate",
)

delta_label = (
    f"{stats['expense_change_pct']}% vs last month"
    if stats["expense_change_pct"] is not None
    else None
)
k4.metric("Top Category", stats["top_category"].replace("_", " ").title(), delta=delta_label)

st.divider()

# TABS
tab_overview, tab_categories, tab_trends, tab_data = st.tabs(
    ["Overview", "Categories", "Trends", "Data & Export"]
)

# Overview Tab
with tab_overview:
    st.subheader("Monthly Summary")
    summary = monthly_summary(df)  # always full range, unaffected by month filter
    st.dataframe(summary, use_container_width=True, hide_index=True)
 
    fig = px.bar(
        summary,
        x="month",
        y=["income", "expense"],
        barmode="group",
        title="Income vs Expense by Month",
    )
    st.plotly_chart(fig, use_container_width=True)

# Categories Tab
with tab_categories:
    st.subheader(f"Spend by Category - {selected_month}")
    breakdown = category_breakdown(df, month = filter_month)

    if breakdown.empty:
        st.warning("No Data for this selection")
    else:
        col1, col2 = st.columns(2)

        with col1:
            fig_bar = px.bar(breakdown, x="category", y="total_spend", title="Category Spend")
            st.plotly_chart(fig_bar, use_container_width=True)
        with col2:
            fig_pie = px.pie(breakdown, names="category", values="total_spend", title="Category Share")
            st.plotly_chart(fig_pie, use_container_width=True)
 
        st.subheader("Top 5 Categories")
        st.dataframe(top_categories(df, n=5, month=filter_month), use_container_width=True, hide_index=True)

# Trends tab
with tab_trends:
    st.subheader("Spending Trend Over Time")
    summary = monthly_summary(df)

    fig_trend = px.line(summary, x="month", y="expense", markers=True, title="Monthly Expense Trend")
    st.plotly_chart(fig_trend, use_container_width=True)
 
    fig_net = px.line(summary, x="month", y="net", markers=True, title="Net (Income - Expense) by Month")
    st.plotly_chart(fig_net, use_container_width=True)

# Data & Export Tab
with tab_data:
    st.subheader("Transactions Data")
    st.caption("Edit the 'category' column below to correct any miscategorized transactions.")
 
    display_cols = ["date_str", "description", "amount", "type", "category"]
    edited = st.data_editor(
        view_df[display_cols].rename(columns={"date_str": "date"}),
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
    )
 
    st.divider()

    st.subheader("Export")
    csv_bytes = edited.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="finsight_transactions.csv",
        mime="text/csv",
    )
 
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        monthly_summary(df).to_excel(writer, sheet_name="Summary", index=False)
        edited.to_excel(writer, sheet_name="Transactions", index=False)
 
    st.download_button(
        "Download Excel Report",
        data=excel_buffer.getvalue(),
        file_name="finsight_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    full_summary = monthly_summary(df)
    forecast_df = forecast_next_n_months(full_summary, n=3) if len(full_summary) >= 2 else None

    pdf_bytes = generate_pdf_report(
        kpi_dict=kpi(df),
        summary_df=full_summary,
        breakdown_df=category_breakdown(df),
        source_name=st.session_state["source"],
        forecast_df=forecast_df,
    )
    st.download_button(
        "Download PDF Report",
        data=pdf_bytes,
        file_name="finsight_report.pdf",
        mime="application/pdf",
    )