"""
Run the BazaarLink SQL scripts against your local MySQL 8 server.

  1. 01_schema.sql   - create database, tables, primary and foreign keys
  2. 02_load.sql     - load the cleaned CSVs (falls back to Python inserts
                       if LOAD DATA LOCAL INFILE is disabled on the server)
  3. 04_views.sql    - create the dashboard views
  4. 03_analysis.sql - run every query, save each result to 04_sql/results/<ID>.csv
                       and write 04_sql/query_results_summary.md
  5. Reconcile SQL-18 headline KPIs with Pandas -> 04_sql/results/reconciliation.csv

Usage (from the project root, in your own terminal):
    pip install mysql-connector-python pandas
    python 04_sql/run_sql.py --user root

The password is asked for at the prompt (never stored in a file).
"""

import argparse
import getpass
import os
import re
import sys
from datetime import datetime

import mysql.connector
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLEAN = os.path.join(ROOT, "02_data", "cleaned")
RESULTS = os.path.join(HERE, "results")

# columns loaded per table, in CSV order (used by the Python fallback loader)
TABLE_COLS = {
    "customers": ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"],
    "sellers": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "products": ["product_id", "product_category_name", "product_name_length", "product_description_length",
                 "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm",
                 "product_width_cm", "product_category_english"],
    "orders": ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"],
    "payments": ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"],
    "reviews": ["review_id", "order_id", "review_score", "review_comment_title", "review_comment_message",
                "review_creation_date", "review_answer_timestamp"],
}


class SqlRunError(Exception):
    """Raised when a SQL script statement fails."""


def split_statements(sql):
    """Split a script on semicolons at line ends; drop comment-only chunks."""
    parts = re.split(r";\s*(?:\n|$)", sql)
    out = []
    for p in parts:
        code = "\n".join(line for line in p.splitlines() if not line.strip().startswith("--")).strip()
        if code:
            out.append(p.strip())
    return out


def run_script(cur, path, replace=None):
    sql = open(path, encoding="utf-8").read()
    for k, v in (replace or {}).items():
        sql = sql.replace(k, v)
    last = None
    for stmt in split_statements(sql):
        try:
            cur.execute(stmt)
            if cur.with_rows:
                last = (cur.column_names, cur.fetchall())
        except mysql.connector.Error as e:
            raise SqlRunError(f"{os.path.basename(path)} failed: {e}\n--- statement ---\n{stmt[:400]}") from e
    return last


def python_load(conn):
    """Fallback loader: insert the cleaned CSVs with executemany."""
    cur = conn.cursor()
    for table, cols in TABLE_COLS.items():
        df = pd.read_csv(os.path.join(CLEAN, f"{table}.csv"), usecols=cols, dtype=str,
                         keep_default_na=False)[cols]
        for col in ("product_name_length", "product_description_length", "product_photos_qty"):
            if col in df:  # "4.0" -> "4" for SMALLINT columns
                df[col] = df[col].str.replace(r"\.0$", "", regex=True)
        df = df.replace({"": None})
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})"
        rows = list(df.itertuples(index=False, name=None))
        for i in range(0, len(rows), 5000):
            cur.executemany(sql, rows[i:i + 5000])
        conn.commit()
        print(f"  {table:12s} {len(rows):>8,} rows (python insert)")


def pandas_kpis():
    """Headline KPIs calculated independently in Pandas from the cleaned CSVs."""
    o = pd.read_csv(os.path.join(CLEAN, "orders.csv"))
    i = pd.read_csv(os.path.join(CLEAN, "order_items.csv"))
    c = pd.read_csv(os.path.join(CLEAN, "customers.csv"))
    r = pd.read_csv(os.path.join(CLEAN, "reviews.csv"))
    deliv = o[o.order_status == "delivered"]
    items_d = i[i.order_id.isin(deliv.order_id)]
    meas = o[o.is_delivery_measurable == 1]
    per_cust = o.merge(c, on="customer_id").groupby("customer_unique_id").order_id.nunique()
    revenue = items_d.price.sum()
    return {
        "orders": o.order_id.nunique(),
        "delivered_orders": len(deliv),
        "revenue": round(revenue, 2),
        "aov": round(revenue / items_d.order_id.nunique(), 2),
        "freight": round(items_d.freight_value.sum(), 2),
        "freight_ratio_pct": round(100 * items_d.freight_value.sum() / revenue, 2),
        "on_time_pct": round(100 * (1 - meas.is_late.mean()), 2),
        "avg_delivery_days": round(meas.delivery_days.mean(), 2),
        "avg_delay_days": round(meas.delay_days.mean(), 2),
        "avg_review_score": round(r.review_score.mean(), 3),
        "negative_review_pct": round(100 * (r.review_score <= 2).mean(), 2),
        "repeat_customer_pct": round(100 * (per_cust >= 2).mean(), 2),
        "cancellation_pct": round(100 * o.is_cancelled.mean(), 2),
    }


def md_table(cols, rows, limit=10):
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in rows[:limit]:
        lines.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    if len(rows) > limit:
        lines.append(f"\n_{len(rows) - limit} more rows in the CSV._")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", default="root")
    args = ap.parse_args()

    for t in TABLE_COLS:
        if not os.path.exists(os.path.join(CLEAN, f"{t}.csv")):
            sys.exit(f"Missing 02_data/cleaned/{t}.csv - run 05_python/src/clean_data.py first "
                     f"(sellers.csv needs olist_sellers_dataset.csv in 02_data/raw/).")

    pwd = os.environ.get("MYSQL_PWD") or getpass.getpass(f"MySQL password for {args.user}@{args.host}: ")
    os.makedirs(RESULTS, exist_ok=True)
    conn = mysql.connector.connect(host=args.host, port=args.port, user=args.user, password=pwd,
                                   allow_local_infile=True, allow_local_infile_in_path=CLEAN)
    cur = conn.cursor()
    start = datetime.now()
    try:
        print("1. Schema ..."); run_script(cur, os.path.join(HERE, "01_schema.sql"))
        print("2. Load ...")
        try:
            cur.execute("SET GLOBAL local_infile = 1")
        except mysql.connector.Error:
            pass
        try:
            cols, rows = run_script(cur, os.path.join(HERE, "02_load.sql"),
                                    {"{DATA_DIR}": CLEAN.replace("\\", "/")})
            conn.commit()
            for r in rows:
                print(f"  {r[0]:12s} {r[1]:>8,} rows")
        except SqlRunError as e:
            print(f"  LOAD DATA not available ({str(e).splitlines()[0][:120]}); using Python inserts")
            run_script(cur, os.path.join(HERE, "01_schema.sql"))
            python_load(conn)
        print("3. Views ..."); run_script(cur, os.path.join(HERE, "04_views.sql"))

        print("4. Analysis queries ...")
        sql = open(os.path.join(HERE, "03_analysis.sql"), encoding="utf-8").read()
        cur.execute("USE bazaarlink")
        summary = [f"# Query results summary\n\nGenerated {datetime.now():%Y-%m-%d %H:%M} by run_sql.py "
                   f"from 03_analysis.sql. Full results: 04_sql/results/<ID>.csv\n"]
        sql18 = None
        for block in re.split(r"^-- @query ", sql, flags=re.M)[1:]:
            header, body = block.split("\n", 1)
            qid, question, title = [x.strip() for x in header.split("|", 2)]
            cur.execute(body.strip().rstrip(";"))
            cols, rows = list(cur.column_names), cur.fetchall()
            pd.DataFrame(rows, columns=cols).to_csv(os.path.join(RESULTS, f"{qid}.csv"), index=False)
            summary.append(f"## {qid} ({question}): {title}\n\n{md_table(cols, rows)}\n")
            print(f"  {qid:8s} {len(rows):>4} rows  {title[:60]}")
            if qid == "SQL-18":
                sql18 = dict(zip(cols, rows[0]))
        with open(os.path.join(HERE, "query_results_summary.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(summary))

        print("5. Reconciliation SQL vs Pandas ...")
        pk = pandas_kpis()
        rec = []
        for k, v in pk.items():
            s = float(sql18[k])
            diff = 0 if v == s else abs(s - v) / abs(v) * 100 if v else float("inf")
            rec.append({"kpi": k, "sql": s, "pandas": v, "diff_pct": round(diff, 4),
                        "within_1pct": "PASS" if diff <= 1 else "FAIL"})
        rec = pd.DataFrame(rec)
        rec.to_csv(os.path.join(RESULTS, "reconciliation.csv"), index=False)
        print(rec.to_string(index=False))
    finally:
        cur.close()
        conn.close()
        print(f"Finished in {(datetime.now() - start).seconds}s")


if __name__ == "__main__":
    main()
