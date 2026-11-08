"""
BazaarLink capstone - Day 2 data cleaning script.

Reads the raw Olist CSV files from 02_data/raw/, fixes types, handles missing
values, duplicates and anomalies, flags IQR outliers, derives delivery columns,
and writes cleaned CSVs to 02_data/cleaned/.

It also writes:
  * 02_data/logs/data_quality_log.csv  - every issue found, the action taken and why
  * 02_data/logs/row_counts.csv        - row counts before and after cleaning

Run from the project root:
    python 05_python/src/clean_data.py
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "02_data", "raw")
CLEAN = os.path.join(ROOT, "02_data", "cleaned")
LOGS = os.path.join(ROOT, "02_data", "logs")

FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translation": "product_category_name_translation.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}
REQUIRED = {"orders", "items", "customers", "payments", "reviews", "products"}

# Analysis window for trends: months before Jan 2017 and after Aug 2018 have
# fewer than 1,000 orders each (incomplete), so they are excluded from trends.
TREND_START = pd.Period("2017-01", "M")
TREND_END = pd.Period("2018-08", "M")

DQ_LOG = []      # data quality log rows
ROW_COUNTS = []  # before/after counts


class MissingFileError(Exception):
    """Raised when a required raw CSV file is not found in 02_data/raw/."""


def log_issue(table, column, issue, rows_affected, action, reason):
    """Add one entry to the data quality log."""
    DQ_LOG.append({
        "id": f"DQ-{len(DQ_LOG) + 1:02d}",
        "table": table,
        "column": column,
        "issue": issue,
        "rows_affected": int(rows_affected),
        "action": action,
        "reason": reason,
        "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })


def read_raw(key):
    """Read one raw CSV. Returns None for optional files that are missing.

    utf-8-sig removes the byte-order mark some files carry in the header.
    pandas' C parser respects quoted fields, so review comments that contain
    commas and line breaks are read correctly.
    """
    path = os.path.join(RAW, FILES[key])
    if not os.path.exists(path):
        if key in REQUIRED:
            raise MissingFileError(f"Required file not found: {path}")
        print(f"WARNING: optional file missing, skipped: {FILES[key]}")
        return None
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df


def iqr_flag(series):
    """Return a boolean Series that is True where a value is an IQR outlier
    (below Q1 - 1.5*IQR or above Q3 + 1.5*IQR). NaN is never flagged."""
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)


def count(name, before, after):
    ROW_COUNTS.append({"table": name, "rows_before": before, "rows_after": after,
                       "difference": before - after})


# --------------------------------------------------------------------------
# Table cleaners
# --------------------------------------------------------------------------

def clean_customers(df):
    """Standardise city/state text. customer_id is unique per order; the real
    customer is customer_unique_id."""
    before = len(df)
    df = df.copy()
    df["customer_city"] = df["customer_city"].str.strip().str.lower()
    df["customer_state"] = df["customer_state"].str.strip().str.upper()
    lost_zero = (df["customer_zip_code_prefix"].astype(str).str.len() < 5).sum()
    df["customer_zip_code_prefix"] = df["customer_zip_code_prefix"].astype(str).str.zfill(5)
    log_issue("customers", "customer_id / customer_unique_id",
              "customer_id changes with every order: 99,441 customer_id values but "
              f"{df['customer_unique_id'].nunique():,} real customers",
              before - df["customer_unique_id"].nunique(), "Kept both; all customer counts use customer_unique_id",
              "Counting customer_id would make the repeat customer rate look like zero")
    log_issue("customers", "customer_zip_code_prefix", "Zip prefix read as a number, leading zeros lost",
              lost_zero, "Converted to 5-character text with leading zeros restored",
              "Zip codes are identifiers, not numbers")
    count("customers", before, len(df))
    return df


def clean_orders(df):
    """Parse dates, flag delivery validity and derive delivery columns."""
    before = len(df)
    df = df.copy()
    date_cols = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
                 "order_delivered_customer_date", "order_estimated_delivery_date"]
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    log_issue("orders", ", ".join(date_cols), "Dates stored as text", before, "Converted to datetime",
              "Needed to calculate delivery days")

    dup = df["order_id"].duplicated().sum()
    log_issue("orders", "order_id", "Duplicate order_id check", dup, "None found" if dup == 0 else "Dropped duplicates",
              "order_id must be unique (primary key)")

    delivered = df["order_status"].eq("delivered")
    missing_deliv = delivered & df["order_delivered_customer_date"].isna()
    log_issue("orders", "order_delivered_customer_date",
              "Blank delivered date (cancelled / not yet delivered orders)", df["order_delivered_customer_date"].isna().sum(),
              "Left blank; delivery KPIs use order_status = 'delivered' only",
              "Orders that were never delivered have no delivery date; filling them would invent data")
    log_issue("orders", "order_delivered_customer_date",
              "Status is 'delivered' but delivered date is blank", missing_deliv.sum(),
              "Kept for revenue (status delivered); excluded from delivery-time KPIs (is_delivery_measurable = 0)",
              "Delivery time cannot be measured without the date; too few rows (8) to affect results")
    odd = (~delivered) & df["order_delivered_customer_date"].notna()
    log_issue("orders", "order_status", "Status is not 'delivered' but a delivered date exists", odd.sum(),
              "Kept status as recorded; excluded from delivery KPIs",
              "BRD rule BR-01: delivery KPIs use delivered status only")
    log_issue("orders", "order_approved_at", "Blank approval date", df["order_approved_at"].isna().sum(),
              "Left blank; stage analysis skips these orders", "Mostly cancelled orders; approval never happened")

    df["is_delivered"] = delivered.astype(int)
    df["is_delivery_measurable"] = (delivered & df["order_delivered_customer_date"].notna()).astype(int)
    df["is_cancelled"] = df["order_status"].isin(["canceled", "unavailable"]).astype(int)

    # Date features
    df["purchase_date"] = df["order_purchase_timestamp"].dt.date
    df["purchase_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    df["purchase_year"] = df["order_purchase_timestamp"].dt.year
    df["purchase_weekday"] = df["order_purchase_timestamp"].dt.day_name()
    df["purchase_hour"] = df["order_purchase_timestamp"].dt.hour
    month_p = df["order_purchase_timestamp"].dt.to_period("M")
    df["in_trend_window"] = ((month_p >= TREND_START) & (month_p <= TREND_END)).astype(int)
    sparse = (df["in_trend_window"] == 0).sum()
    log_issue("orders", "order_purchase_timestamp",
              "Sparse months: Sep-Dec 2016 and Sep-Oct 2018 have fewer than 1,000 orders each (2016-11 has none)",
              sparse, "Flagged in_trend_window = 0; excluded from trend analysis only",
              "Incomplete months would distort monthly trends")

    # Delivery durations in days (fractional days, rounded to 2 dp)
    day = np.timedelta64(1, "D")
    m = df["is_delivery_measurable"] == 1
    df["delivery_days"] = ((df["order_delivered_customer_date"] - df["order_purchase_timestamp"]) / day).where(m).round(2)
    df["estimated_days"] = ((df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]) / day).where(m).round(2)
    # The estimated delivery date has no time (always 00:00), so delay is measured
    # in whole calendar days: same as MySQL DATEDIFF(delivered, estimated).
    df["delay_days"] = ((df["order_delivered_customer_date"].dt.normalize()
                         - df["order_estimated_delivery_date"].dt.normalize()) / day).where(m)
    df["approval_days"] = ((df["order_approved_at"] - df["order_purchase_timestamp"]) / day).where(m).round(2)
    df["seller_handover_days"] = ((df["order_delivered_carrier_date"] - df["order_approved_at"]) / day).where(m).round(2)
    df["carrier_days"] = ((df["order_delivered_customer_date"] - df["order_delivered_carrier_date"]) / day).where(m).round(2)

    neg_hand = (df["seller_handover_days"] < 0).sum()
    log_issue("orders", "order_delivered_carrier_date",
              "Carrier pickup date is before payment approval date (negative seller handover days)", neg_hand,
              "Flagged stage_timestamp_issue = 1; seller_handover_days set to blank for these rows",
              "Impossible sequence (likely timestamp entry error); would distort stage analysis. "
              "Order is still used for total delivery time and on-time rate")
    neg_car = (df["carrier_days"] < 0).sum()
    log_issue("orders", "order_delivered_customer_date",
              "Customer delivery date is before carrier pickup date (negative carrier days)", neg_car,
              "Flagged stage_timestamp_issue = 1; carrier_days set to blank for these rows", "Impossible sequence")
    df["stage_timestamp_issue"] = ((df["seller_handover_days"] < 0) | (df["carrier_days"] < 0)).astype(int)
    df.loc[df["seller_handover_days"] < 0, "seller_handover_days"] = np.nan
    df.loc[df["carrier_days"] < 0, "carrier_days"] = np.nan

    # On-time definition: delivered DATE on or before estimated date (BRD KPI)
    on_time = df["delay_days"] <= 0
    log_issue("orders", "order_estimated_delivery_date",
              "Estimated date has no time of day; delivered date has a time", int(m.sum()),
              "On-time and delay days compare calendar dates (delivered date <= estimated date)",
              "An order delivered at 15:00 on the promised date met the promise; same rule as SQL DATEDIFF")
    df["is_late"] = np.where(m, (~on_time).astype(int), np.nan)
    df["delivery_status"] = np.where(~m, "Not delivered", np.where(on_time, "On time", "Late"))
    # Delay buckets (BRD BR-06), in whole days late.
    df["delay_bucket"] = np.select(
        [~m, df["is_late"] == 0, df["delay_days"] <= 3, df["delay_days"] <= 7],
        ["Not delivered", "On time", "1-3 days late", "4-7 days late"],
        default="8+ days late")

    df["delivery_days_outlier"] = iqr_flag(df["delivery_days"]).astype(int)
    log_issue("orders", "delivery_days", "IQR outliers (very long deliveries)", df["delivery_days_outlier"].sum(),
              "Flagged delivery_days_outlier = 1; NOT removed",
              "Long deliveries are real customer experiences and the core of the business problem; "
              "removing them would understate lateness. Robust tests (median, Mann-Whitney) are used instead")
    count("orders", before, len(df))
    return df


def clean_items(df):
    """Check keys and values; flag outliers. One row per item, so it is never
    joined to payments/reviews before being aggregated to order level."""
    before = len(df)
    df = df.copy()
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    dup = df.duplicated(["order_id", "order_item_id"]).sum()
    log_issue("order_items", "order_id + order_item_id", "Duplicate key check", dup,
              "None found" if dup == 0 else "Dropped duplicates", "Composite primary key must be unique")
    multi = (df.groupby("order_id").size() > 1).sum()
    log_issue("order_items", "order_id", "One order can have many item rows", multi,
              "Aggregated to order level (orders_master) before joining to payments or reviews",
              "Joining item rows to payments/reviews would double count totals")
    df["price_outlier"] = iqr_flag(df["price"]).astype(int)
    df["freight_outlier"] = iqr_flag(df["freight_value"]).astype(int)
    log_issue("order_items", "price", "IQR outliers (high-priced items)", df["price_outlier"].sum(),
              "Flagged price_outlier = 1; NOT removed",
              "High prices are genuine sales (e.g. furniture, electronics); removing them would understate revenue")
    log_issue("order_items", "freight_value", "IQR outliers (high freight)", df["freight_outlier"].sum(),
              "Flagged freight_outlier = 1; NOT removed", "Genuine charges for heavy items / remote states; needed for Q13")
    count("order_items", before, len(df))
    return df


def clean_payments(df):
    """Fix impossible instalment values. Payments are summed per order, never
    after a join to order_items."""
    before = len(df)
    df = df.copy()
    zero_inst = (df["payment_installments"] == 0).sum()
    df.loc[df["payment_installments"] == 0, "payment_installments"] = 1
    log_issue("payments", "payment_installments", "Instalments = 0", zero_inst, "Set to 1",
              "Every payment is at least one instalment")
    log_issue("payments", "payment_type", "Payment type 'not_defined'", (df["payment_type"] == "not_defined").sum(),
              "Kept as 'not_defined'", "Too few rows to matter; no reliable way to infer the real type")
    log_issue("payments", "payment_value", "Payment value = 0 (vouchers)", (df["payment_value"] == 0).sum(),
              "Kept", "Valid zero-value voucher lines")
    log_issue("payments", "payment_value",
              "Payment totals include freight and instalment interest, so they differ from item revenue", 0,
              "Revenue is taken from order_items.price only (BRD KPI); payments used for payment-type analysis",
              "Explains why Finance's payment totals never match item revenue")
    count("payments", before, len(df))
    return df


def clean_reviews(df):
    """Keep one review per order (the latest) and clean comment text."""
    before = len(df)
    df = df.copy()
    for c in ["review_creation_date", "review_answer_timestamp"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    log_issue("reviews", "review_id", "Same review_id linked to more than one order", df["review_id"].duplicated().sum(),
              "Kept (each row belongs to a different order); review table keyed on order_id",
              "One review covering several orders placed together; still one review per order")
    dup_orders = df["order_id"].duplicated().sum()
    df = df.sort_values(["order_id", "review_creation_date", "review_answer_timestamp"])
    df = df.drop_duplicates("order_id", keep="last")
    log_issue("reviews", "order_id", "Orders with more than one review", dup_orders,
              "Kept only the latest review per order",
              "Averaging scores must be at order level; the latest review is the customer's final opinion")
    for c in ["review_comment_title", "review_comment_message"]:
        has_break = df[c].fillna("").str.contains(r"[\r\n]").sum()
        df[c] = df[c].fillna("").str.replace(r"[\r\n]+", " ", regex=True).str.strip()
        log_issue("reviews", c, "Comment contains line breaks", has_break, "Replaced line breaks with a space",
                  "Line breaks and commas break plain CSV import into SQL")
    log_issue("reviews", "review_comment_message", "Blank comment (score only)", (df["review_comment_message"] == "").sum(),
              "Filled with empty text; has_comment flag added", "Many customers give a score without a comment; not an error")
    df["has_comment"] = (df["review_comment_message"] != "").astype(int)
    df["is_negative"] = df["review_score"].le(2).astype(int)
    count("reviews", before, len(df))
    return df


def clean_products(df, translation):
    """Rename misspelt columns, translate categories, fill missing values."""
    before = len(df)
    df = df.copy()
    renames = {"product_name_lenght": "product_name_length",
               "product_description_lenght": "product_description_length"}
    df = df.rename(columns=renames)
    log_issue("products", "product_name_lenght, product_description_lenght", "Misspelt column names", 0,
              "Renamed to product_name_length, product_description_length", "Consistent names; recorded in data dictionary")
    miss_cat = df["product_category_name"].isna().sum()
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    log_issue("products", "product_category_name", "Missing category", miss_cat, "Labelled 'unknown'",
              "BRD rule BR-08; keeps these products' revenue in totals")

    if translation is not None:
        translation = translation.copy()
        typo_fix = {"costruction": "construction", "fashio_female": "fashion_female", "home_confort": "home_comfort"}
        before_fix = translation["product_category_name_english"].copy()
        for bad, good in typo_fix.items():
            translation["product_category_name_english"] = translation["product_category_name_english"].str.replace(bad, good)
        log_issue("translation", "product_category_name_english",
                  "Spelling errors in English names (costruction, fashio_female, home_confort)",
                  (before_fix != translation["product_category_name_english"]).sum(),
                  "Corrected the spelling", "Clean labels on dashboards; recorded so names can be traced to the source")
        tmap = dict(zip(translation["product_category_name"], translation["product_category_name_english"]))
        # Two categories are missing from the translation file: translated by hand
        manual = {"pc_gamer": "pc_gamer", "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers"}
        untranslated = ~df["product_category_name"].isin(tmap)
        n_untranslated = untranslated.sum()
        tmap.update(manual)
        tmap["unknown"] = "unknown"
        df["product_category_english"] = df["product_category_name"].map(tmap)
        still = df["product_category_english"].isna()
        df.loc[still, "product_category_english"] = df.loc[still, "product_category_name"]
        log_issue("products", "product_category_name", "Category names in Portuguese", len(df),
                  "Joined translation file (read with utf-8-sig to remove BOM)", "Dashboards are in English")
        log_issue("products", "product_category_name",
                  "Categories not in the translation file (pc_gamer, portateis_cozinha_e_preparadores_de_alimentos)",
                  n_untranslated, "Translated by hand (pc_gamer, portable_kitchen_food_preparers)",
                  "Keeps every product's category readable in English")
    else:
        df["product_category_english"] = df["product_category_name"]
        log_issue("products", "product_category_name", "Translation file not yet available", len(df),
                  "Portuguese names kept temporarily; re-run this script after adding the file", "File missing in 02_data/raw")

    zero_w = (df["product_weight_g"] == 0).sum()
    df.loc[df["product_weight_g"] == 0, "product_weight_g"] = np.nan
    log_issue("products", "product_weight_g", "Weight = 0 g", zero_w, "Treated as missing",
              "A physical product cannot weigh 0 g")
    dims = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    miss_dims = df[dims].isna().any(axis=1).sum()
    for c in dims:
        df[c] = df[c].fillna(df.groupby("product_category_name")[c].transform("median"))
        df[c] = df[c].fillna(df[c].median())
    log_issue("products", ", ".join(dims), "Missing weight / dimensions", miss_dims,
              "Filled with the median of the product's category", "Median is robust to outliers; needed for the Q10 regression")
    log_issue("products", "product_name_length, product_description_length, product_photos_qty",
              "Missing listing details", df["product_photos_qty"].isna().sum(), "Left blank",
              "Not used in any business question; filling would invent data")
    df["product_volume_cm3"] = df["product_length_cm"] * df["product_height_cm"] * df["product_width_cm"]
    df["weight_outlier"] = iqr_flag(df["product_weight_g"]).astype(int)
    log_issue("products", "product_weight_g", "IQR outliers (heavy products)", df["weight_outlier"].sum(),
              "Flagged weight_outlier = 1; NOT removed", "Heavy products are real and matter for freight and delivery time")
    count("products", before, len(df))
    return df


def clean_sellers(df):
    """Standardise seller location text."""
    before = len(df)
    df = df.copy()
    df["seller_city"] = df["seller_city"].str.strip().str.lower()
    df["seller_state"] = df["seller_state"].str.strip().str.upper()
    df["seller_zip_code_prefix"] = df["seller_zip_code_prefix"].astype(str).str.zfill(5)
    log_issue("sellers", "seller_id", "Duplicate check", df["seller_id"].duplicated().sum(), "None expected", "Primary key")
    count("sellers", before, len(df))
    return df


def clean_geolocation(df):
    """Remove exact duplicates and reduce to one coordinate per zip prefix."""
    before = len(df)
    dups = df.duplicated().sum()
    df = df.drop_duplicates()
    df = (df.assign(geolocation_zip_code_prefix=df["geolocation_zip_code_prefix"].astype(str).str.zfill(5))
            .groupby("geolocation_zip_code_prefix", as_index=False)
            .agg(lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean"),
                 geolocation_state=("geolocation_state", "first")))
    log_issue("geolocation", "all", "Exact duplicate rows; many rows per zip prefix", dups,
              "Dropped duplicates; averaged to one lat/lng per zip prefix",
              "Optional stretch goal (distance); one point per zip is enough")
    count("geolocation", before, len(df))
    return df


# --------------------------------------------------------------------------
# Order-level master table
# --------------------------------------------------------------------------

def build_orders_master(orders, items, customers, payments, reviews, products, sellers):
    """One row per order. Items and payments are aggregated to order level
    BEFORE joining, so nothing is double counted."""
    it = items.merge(products[["product_id", "product_category_english", "product_weight_g"]], on="product_id", how="left")
    if sellers is not None:
        it = it.merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
    else:
        it["seller_state"] = np.nan
    it = it.sort_values(["order_id", "order_item_id"])
    item_agg = it.groupby("order_id").agg(
        n_items=("order_item_id", "count"),
        item_revenue=("price", "sum"),
        freight_value=("freight_value", "sum"),
        total_weight_g=("product_weight_g", "sum"),
        n_sellers=("seller_id", "nunique"),
        primary_seller_id=("seller_id", "first"),
        primary_seller_state=("seller_state", "first"),
        primary_category=("product_category_english", "first"),
    ).reset_index()

    pay_main = (payments.sort_values(["order_id", "payment_value"], ascending=[True, False])
                        .drop_duplicates("order_id")[["order_id", "payment_type"]]
                        .rename(columns={"payment_type": "main_payment_type"}))
    pay_agg = payments.groupby("order_id").agg(
        payment_total=("payment_value", "sum"),
        max_installments=("payment_installments", "max"),
        n_payment_lines=("payment_sequential", "count")).reset_index().merge(pay_main, on="order_id")

    m = (orders.merge(customers[["customer_id", "customer_unique_id", "customer_city", "customer_state"]],
                      on="customer_id", how="left")
               .merge(item_agg, on="order_id", how="left")
               .merge(pay_agg, on="order_id", how="left")
               .merge(reviews[["order_id", "review_score", "is_negative"]], on="order_id", how="left"))
    m["same_state"] = np.where(m["primary_seller_state"].isna(), np.nan,
                               (m["primary_seller_state"] == m["customer_state"]).astype(float))
    for c in ["n_items", "item_revenue", "freight_value"]:
        m[c] = m[c].fillna(0)

    # Customer order sequence (by customer_unique_id) for retention analysis
    m = m.sort_values(["customer_unique_id", "order_purchase_timestamp"])
    m["customer_order_number"] = m.groupby("customer_unique_id").cumcount() + 1
    m["customer_total_orders"] = m.groupby("customer_unique_id")["order_id"].transform("count")
    m["is_first_order"] = (m["customer_order_number"] == 1).astype(int)

    log_issue("orders_master", "order_id", "Orders with no items (mostly unavailable / cancelled)",
              (m["n_items"] == 0).sum(), "Kept with revenue 0", "Needed for cancellation rate; no revenue to count")
    log_issue("orders_master", "order_id", "Orders with no review", m["review_score"].isna().sum(),
              "Kept; review KPIs use reviewed orders only", "Not every customer leaves a review")
    log_issue("orders_master", "order_id", "Orders with more than one seller", (m["n_sellers"] > 1).sum(),
              "Primary seller/category = first item in the order; seller scorecard uses item-level data",
              "Order-level table needs one seller; item-level views keep all sellers")
    return m


def save(df, name):
    path = os.path.join(CLEAN, f"{name}.csv")
    # Unix line endings so MySQL LOAD DATA ... LINES TERMINATED BY '\n' works on any OS
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"  saved {name}.csv  ({len(df):,} rows, {df.shape[1]} cols)")


def main():
    start = datetime.now()
    os.makedirs(CLEAN, exist_ok=True)
    os.makedirs(LOGS, exist_ok=True)
    try:
        raw = {k: read_raw(k) for k in FILES}
        for k, df in raw.items():
            if df is not None and k != "geolocation":  # geolocation logged in clean_geolocation
                log_issue(k, "all", "Exact duplicate rows", df.duplicated().sum(),
                          "Dropped" if df.duplicated().sum() else "None found", "Duplicates double count")
        customers = clean_customers(raw["customers"])
        orders = clean_orders(raw["orders"])
        items = clean_items(raw["items"])
        payments = clean_payments(raw["payments"])
        reviews = clean_reviews(raw["reviews"])
        products = clean_products(raw["products"], raw["translation"])
        sellers = clean_sellers(raw["sellers"]) if raw["sellers"] is not None else None
        geo = clean_geolocation(raw["geolocation"]) if raw["geolocation"] is not None else None
        master = build_orders_master(orders, items, customers, payments, reviews, products, sellers)

        print("Writing cleaned files:")
        for name, df in [("customers", customers), ("orders", orders), ("order_items", items),
                         ("payments", payments), ("reviews", reviews), ("products", products),
                         ("sellers", sellers), ("geolocation_zip", geo), ("orders_master", master)]:
            if df is not None:
                save(df, name)
        count("orders_master", len(orders), len(master))
    except MissingFileError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        pd.DataFrame(DQ_LOG).to_csv(os.path.join(LOGS, "data_quality_log.csv"), index=False)
        pd.DataFrame(ROW_COUNTS).to_csv(os.path.join(LOGS, "row_counts.csv"), index=False)
        print(f"Logged {len(DQ_LOG)} data quality entries. Finished in {(datetime.now() - start).seconds}s")


if __name__ == "__main__":
    main()
