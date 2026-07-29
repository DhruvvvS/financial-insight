import pandas as pd

def monthly_summary(df):
    work = df.copy()
    work['period'] = work["date"].dt.to_period("M")

    income = (
        work[work["amount"] > 0]
        .groupby('period')["amount"]
        .sum()
        .rename("income")
    )

    expense = (
        work[work["amount"] < 0]
        .groupby('period')["amount"]
        .sum()
        .abs()
        .rename("expense")
    )

    summary = pd.concat([income, expense], axis=1).fillna(0).reset_index()
    summary["net"] = summary["income"] - summary["expense"]
    summary = summary.sort_values("period").reset_index(drop=True)
 
    # Display label to match cleaner.py's "month" column format ("Feb 2026")
    summary["month"] = summary["period"].dt.strftime("%b %Y")
    summary = summary.drop(columns=["period"])
    summary = summary[["month", "income", "expense", "net"]]
    return summary

def category_breakdown(df, month = None):

    expenses = df[df["amount"] < 0].copy()
    if month is not None:
        expenses = expenses[expenses["month"] == month]
 
    breakdown = (
        expenses.groupby("category")["amount"]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"amount": "total_spend"})
        .sort_values("total_spend", ascending=False)
        .reset_index(drop=True)
    )
    return breakdown
 
 
def top_categories(df, n=5, month=None):
    """Convenience wrapper: the top-N spend categories."""
    return category_breakdown(df, month=month).head(n)

# Headline KPI for st.metric cards

def kpi(df):

    summary = monthly_summary(df)

    total_income = df[df["amount"] > 0]["amount"].sum()
    total_expense = df[df["amount"] < 0]["amount"].sum().__abs__()
    net = total_income - total_expense
    if total_income > 0:
        savings_rate = (net / total_income * 100)
    else:
        0

    breakdown = category_breakdown(df)
    top_category = breakdown["category"].iloc[0] if not breakdown.empty else "N/A"

    expense_change_pct = None
    if len(summary) >= 2:
        last_expense = summary.iloc[-1]["expense"]
        prev_expense = summary.iloc[-2]["expense"]
        expense_change_pct = round((last_expense - prev_expense) / prev_expense * 100, 1) if prev_expense else None

    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net": round(net, 2),
        "savings_rate_pct": round(savings_rate, 1),
        "top_category": top_category,
        "expense_change_pct": expense_change_pct,  # None if not enough months yet
    }


def main():
    from pathlib import Path
    from cleaner import load_categories, clean_transactions
 
    BASE = Path(__file__).resolve().parent.parent
    raw = pd.read_csv(BASE / "data" / "sample_transactions.csv")
    categories = load_categories(BASE / "categories.json")
    df = clean_transactions(raw, categories)
 
    print("=== Monthly Summary ===")
    print(monthly_summary(df))
 
    print("\n=== Category Breakdown ===")
    print(category_breakdown(df))

    print("\n=== KPI ===")
    print(kpi(df))

if __name__ == "__main__":
    main()