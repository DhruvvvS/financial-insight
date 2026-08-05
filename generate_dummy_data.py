"""
generate_dummy_data.py
-----------------------
Generates 3-6 months of realistic dummy bank/expense transactions for
the FinSight project (demo dataset + test data).

Usage:
    python generate_dummy_data.py
    python generate_dummy_data.py --months 6 --seed 42 --out data/sample_transactions.csv

Output columns: date, description, amount, type
    - date is in DD-MM-YYYY format (Indian convention)
    - amount is POSITIVE for income, NEGATIVE for expenses (bank-statement style)
    - type is "credit" or "debit"

The generator intentionally injects a few realistic quirks so your
cleaning/categorization/anomaly-detection code has real work to do:
    - Recurring fixed transactions (rent, salary) on roughly the same day each month
    - Variable day-to-day spends (food, transport, shopping) at random days
    - A handful of "anomaly" transactions (unusually large one-off expenses)
    - Slightly messy description text (mixed case, extra spaces, vendor codes)
      to mimic real bank statement exports
"""

# Imports
import argparse
import random
from datetime import date, timedelta
import calendar
import csv
import os

# Argument parsing
def parse_args():
    parser = argparse.ArgumentParser(description="Generate dummy transactions for FinSight")
    parser.add_argument("--months", type=int, default=6, help="Number of months of history (3-6 recommended)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out", type=str, default="data/sample_transactions.csv", help="Output CSV path")
    return parser.parse_args()


# ---- Vendor pools (messy, real-world-ish description text) ----------------

INCOME_SOURCES = [
    ("SALARY CREDIT - ACME CORP", (35000, 45000)),
    ("FREELANCE PAYMENT - UPWORK", (3000, 12000)),
    ("INTEREST CREDIT SAVINGS A/C", (50, 400)),
]

RECURRING_EXPENSES = [
    ("RENT PAYMENT TO LANDLORD", (9000, 9000)),
    ("ELECTRICITY BILL BSES", (900, 2200)),
    ("MOBILE RECHARGE JIO", (299, 599)),
    ("BROADBAND BILL ACT FIBERNET", (799, 799)),
    ("GYM MEMBERSHIP FITCLUB", (1200, 1200)),
]

VARIABLE_EXPENSES = [
    ("SWIGGY ORDER #{code}", (150, 650)),
    ("ZOMATO ORDER #{code}", (150, 700)),
    ("BIGBASKET GROCERY", (600, 2800)),
    ("DMART RETAIL PURCHASE", (400, 3200)),
    ("UBER TRIP {code}", (100, 450)),
    ("OLA CAB {code}", (90, 400)),
    ("PETROL PUMP HP {code}", (500, 1500)),
    ("AMAZON.IN PURCHASE", (299, 4500)),
    ("FLIPKART ORDER", (349, 3800)),
    ("NETFLIX SUBSCRIPTION", (199, 649)),
    ("STARBUCKS COFFEE", (250, 600)),
    ("PHARMACY APOLLO", (150, 1200)),
    ("MOVIE TICKETS PVR", (400, 1200)),
    ("SALON GROOMING", (300, 1500)),
]

ANOMALY_EXPENSES = [
    ("LAPTOP PURCHASE - CROMA", (45000, 75000)),
    ("HOSPITAL BILL - APOLLO", (8000, 25000)),
    ("FLIGHT BOOKING - MAKEMYTRIP", (6000, 18000)),
    ("HOME APPLIANCE - RELIANCE DIGITAL", (10000, 30000)),
    ("VEHICLE REPAIR - SERVICE CENTER", (5000, 15000)),
]

# Helper function for generating random days within a month
def random_day_in_month(year, month, day_hint=None, spread=3):

    last_day = calendar.monthrange(year, month)[1]
    if day_hint:
        day = min(max(1, day_hint + random.randint(-spread, spread)), last_day)
    else:
        day = random.randint(1, last_day)
    return date(year, month, day)

# Generate a list of (year, month) tuples for the last `months_back` months
def month_range(months_back):

    today = date.today()
    y, m = today.year, today.month
    months = []
    for _ in range(months_back):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))

# Generate dummy transactions for the specified number of months
def generate_transactions(months_back, seed):
    random.seed(seed)
    rows = []

    for (year, month) in month_range(months_back):
        # --- Income ---
        # Salary lands around the 1st, freelance/interest are occasional
        salary_desc, salary_range = INCOME_SOURCES[0]
        salary_date = random_day_in_month(year, month, day_hint=1, spread=1)
        rows.append([salary_date, salary_desc, round(random.uniform(*salary_range), 2), "credit"])

        if random.random() < 0.5:  # not every month has freelance income
            desc, rng = INCOME_SOURCES[1]
            d = random_day_in_month(year, month)
            rows.append([d, desc, round(random.uniform(*rng), 2), "credit"])

        if random.random() < 0.7:
            desc, rng = INCOME_SOURCES[2]
            d = random_day_in_month(year, month, day_hint=28, spread=2)
            rows.append([d, desc, round(random.uniform(*rng), 2), "credit"])

        # --- Recurring fixed expenses ---
        for desc, rng in RECURRING_EXPENSES:
            d = random_day_in_month(year, month, day_hint=random.choice([3, 5, 7, 10]), spread=2)
            amt = round(random.uniform(*rng), 2)
            rows.append([d, desc, -amt, "debit"])

        # --- Variable day-to-day expenses (15-25 per month) ---
        num_variable = random.randint(15, 25)
        for _ in range(num_variable):
            desc_template, rng = random.choice(VARIABLE_EXPENSES)
            code = random.randint(1000, 9999)
            desc = desc_template.format(code=code) if "{code}" in desc_template else desc_template
            d = random_day_in_month(year, month)
            amt = round(random.uniform(*rng), 2)
            rows.append([d, desc, -amt, "debit"])

        # --- Occasional anomaly (roughly 1 every 2-3 months) ---
        if random.random() < 0.4:
            desc, rng = random.choice(ANOMALY_EXPENSES)
            d = random_day_in_month(year, month)
            amt = round(random.uniform(*rng), 2)
            rows.append([d, desc, -amt, "debit"])

    # Sort chronologically (date objects sort correctly natively)
    rows.sort(key=lambda r: r[0])
    return rows

# Write the generated transactions to a CSV file
def write_csv(rows, out_path):

    os.makedirs(os.path.dirname(out_path), exist_ok=True) if os.path.dirname(out_path) else None
    formatted_rows = [
        [d.strftime("%d-%m-%Y"), description, amount, txn_type]
        for d, description, amount, txn_type in rows
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "description", "amount", "type"])
        writer.writerows(formatted_rows)

# MAIN Function for testing the module independently
def main():
    args = parse_args()
    rows = generate_transactions(args.months, args.seed)
    write_csv(rows, args.out)

    total_credit = sum(r[2] for r in rows if r[2] > 0)
    total_debit = sum(-r[2] for r in rows if r[2] < 0)

    print(f"Generated {len(rows)} transactions across {args.months} months")
    print(f"Saved to: {args.out}")
    print(f"Total income:   {total_credit:,.2f}")
    print(f"Total expenses: {total_debit:,.2f}")
    print(f"Net:            {total_credit - total_debit:,.2f}")


if __name__ == "__main__":
    main()