"""
Build 02_data/data_dictionary_and_dq_log.xlsx from the cleaned CSVs and the
logs written by clean_data.py. Run after clean_data.py:

    python 05_python/src/build_data_dictionary.py
"""

import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLEAN = os.path.join(ROOT, "02_data", "cleaned")
LOGS = os.path.join(ROOT, "02_data", "logs")
OUT = os.path.join(ROOT, "02_data", "data_dictionary_and_dq_log.xlsx")

TABLES = {
    "orders": ("One row per order", "olist_orders_dataset.csv", "order_id"),
    "order_items": ("One row per item in an order", "olist_order_items_dataset.csv", "order_id + order_item_id"),
    "customers": ("One row per customer_id (one per order)", "olist_customers_dataset.csv", "customer_id"),
    "payments": ("One row per payment line", "olist_order_payments_dataset.csv", "order_id + payment_sequential"),
    "reviews": ("One review per order (latest kept)", "olist_order_reviews_dataset.csv", "order_id"),
    "products": ("One row per product", "olist_products_dataset.csv + translation", "product_id"),
    "sellers": ("One row per seller", "olist_sellers_dataset.csv", "seller_id"),
    "geolocation_zip": ("One row per zip prefix (averaged)", "olist_geolocation_dataset.csv", "geolocation_zip_code_prefix"),
    "orders_master": ("One row per order with customer, item, payment and review data aggregated", "Derived (all tables)", "order_id"),
}

DESC = {
    "order_id": "Unique order identifier",
    "customer_id": "Customer key for this order (changes with every order)",
    "customer_unique_id": "Real customer identifier; use for customer counts and repeat rate",
    "customer_zip_code_prefix": "First 5 digits of customer zip code (text)",
    "customer_city": "Customer city (lower case)",
    "customer_state": "Customer state, 2-letter code",
    "order_status": "Order status (delivered, shipped, canceled, unavailable, invoiced, processing, created, approved)",
    "order_purchase_timestamp": "Date and time the order was placed",
    "order_approved_at": "Date and time payment was approved",
    "order_delivered_carrier_date": "Date and time the seller handed the order to the carrier",
    "order_delivered_customer_date": "Date and time the order reached the customer",
    "order_estimated_delivery_date": "Delivery date promised at checkout (date only)",
    "is_delivered": "1 if order_status = 'delivered' (used for Revenue / AOV)",
    "is_delivery_measurable": "1 if delivered AND delivered date present (used for all delivery KPIs)",
    "is_cancelled": "1 if status is canceled or unavailable",
    "purchase_date": "Purchase date (no time)",
    "purchase_month": "Purchase month, YYYY-MM",
    "purchase_year": "Purchase year",
    "purchase_weekday": "Purchase day of week",
    "purchase_hour": "Purchase hour (0-23)",
    "in_trend_window": "1 if month is Jan 2017 - Aug 2018 (complete months used for trends)",
    "delivery_days": "Delivered date minus purchase timestamp, in days (KPI: Average delivery days)",
    "estimated_days": "Estimated date minus purchase timestamp, in days (promised lead time)",
    "delay_days": "Delivered date minus estimated date in whole calendar days; positive = late (KPI: Delay days)",
    "approval_days": "Approval minus purchase, in days (stage 1)",
    "seller_handover_days": "Carrier date minus approval, in days (stage 2, KPI: Seller handover days); blank if timestamps out of order",
    "carrier_days": "Delivered date minus carrier date, in days (stage 3); blank if timestamps out of order",
    "stage_timestamp_issue": "1 if stage timestamps are in an impossible order",
    "is_late": "1 if delay_days > 0, 0 if on time, blank if not measurable",
    "delivery_status": "On time / Late / Not delivered (calculated column)",
    "delay_bucket": "On time, 1-3 days late, 4-7 days late, 8+ days late, Not delivered",
    "delivery_days_outlier": "1 if delivery_days is an IQR outlier (flagged, not removed)",
    "order_item_id": "Item sequence number within the order (1, 2, 3...)",
    "product_id": "Product identifier",
    "seller_id": "Seller identifier",
    "shipping_limit_date": "Deadline for seller to hand the item to the carrier",
    "price": "Item price in BRL, excluding freight (KPI: Revenue)",
    "freight_value": "Freight charged for the item in BRL (KPI: Freight cost)",
    "price_outlier": "1 if price is an IQR outlier (flagged, not removed)",
    "freight_outlier": "1 if freight_value is an IQR outlier (flagged, not removed)",
    "payment_sequential": "Payment line number within the order",
    "payment_type": "credit_card, boleto, voucher, debit_card, not_defined",
    "payment_installments": "Number of instalments (0 corrected to 1)",
    "payment_value": "Amount paid on this line in BRL (includes freight; not used for revenue)",
    "review_id": "Review identifier (can repeat across orders)",
    "review_score": "Review score 1 to 5",
    "review_comment_title": "Review title (line breaks removed; blank if none)",
    "review_comment_message": "Review comment (line breaks removed; blank if none)",
    "review_creation_date": "Date the review survey was sent",
    "review_answer_timestamp": "Date and time the customer answered",
    "has_comment": "1 if the review has a comment",
    "is_negative": "1 if review_score is 1 or 2 (KPI: Negative review rate)",
    "product_category_name": "Category name in Portuguese; 'unknown' if missing",
    "product_category_english": "Category name in English",
    "product_name_length": "Characters in product name (renamed from product_name_lenght)",
    "product_description_length": "Characters in description (renamed from product_description_lenght)",
    "product_photos_qty": "Number of product photos",
    "product_weight_g": "Weight in grams (0 and missing filled with category median)",
    "product_length_cm": "Length in cm", "product_height_cm": "Height in cm", "product_width_cm": "Width in cm",
    "product_volume_cm3": "Length x height x width",
    "weight_outlier": "1 if weight is an IQR outlier (flagged, not removed)",
    "seller_zip_code_prefix": "Seller zip prefix (text)", "seller_city": "Seller city (lower case)", "seller_state": "Seller state, 2-letter code",
    "geolocation_zip_code_prefix": "Zip prefix (text)", "lat": "Average latitude", "lng": "Average longitude", "geolocation_state": "State",
    "n_items": "Number of items in the order",
    "item_revenue": "Sum of item prices for the order (Revenue counts delivered orders only)",
    "total_weight_g": "Total product weight in the order",
    "n_sellers": "Number of distinct sellers in the order",
    "primary_seller_id": "Seller of the first item",
    "primary_seller_state": "State of the first item's seller",
    "primary_category": "Category (English) of the first item",
    "payment_total": "Sum of payment_value for the order",
    "max_installments": "Highest instalment count used",
    "n_payment_lines": "Number of payment lines",
    "main_payment_type": "Payment type with the largest value",
    "same_state": "1 if primary seller state = customer state, 0 if inter-state",
    "customer_order_number": "1 for the customer's first order, 2 for second...",
    "customer_total_orders": "Total orders by this customer_unique_id",
    "is_first_order": "1 if this is the customer's first order",
}


def main():
    rows = []
    for t, (grain, src, pk) in TABLES.items():
        path = os.path.join(CLEAN, f"{t}.csv")
        if not os.path.exists(path):
            rows.append({"table": t, "column": "(file not yet available)", "data_type": "", "description": grain,
                         "source": src, "primary_key": pk, "null_count": "", "example": ""})
            continue
        df = pd.read_csv(path, low_memory=False)
        for c in df.columns:
            ex = df[c].dropna()
            rows.append({"table": t, "column": c, "data_type": str(df[c].dtype), "description": DESC.get(c, ""),
                         "source": src, "primary_key": "Yes" if c in pk.split(" + ") else "",
                         "null_count": int(df[c].isna().sum()), "example": str(ex.iloc[0])[:60] if len(ex) else ""})
    dd = pd.DataFrame(rows)
    dq = pd.read_csv(os.path.join(LOGS, "data_quality_log.csv"))
    rc = pd.read_csv(os.path.join(LOGS, "row_counts.csv"))
    tables = pd.DataFrame([(t, g, s, k) for t, (g, s, k) in TABLES.items()],
                          columns=["table", "grain (one row is)", "source", "primary key"])

    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        tables.to_excel(xw, sheet_name="Tables", index=False)
        dd.to_excel(xw, sheet_name="Data Dictionary", index=False)
        dq.to_excel(xw, sheet_name="Data Quality Log", index=False)
        rc.to_excel(xw, sheet_name="Row Counts", index=False)

    wb = load_workbook(OUT)
    hdr = PatternFill("solid", fgColor="1F3A5F")
    thin = Side(style="thin", color="BFBFBF")
    widths = {"Tables": [18, 60, 40, 28], "Data Dictionary": [16, 30, 10, 70, 30, 10, 10, 30],
              "Data Quality Log": [7, 14, 30, 55, 12, 55, 60, 16], "Row Counts": [16, 14, 14, 12]}
    for ws in wb:
        for c in ws[1]:
            c.fill = hdr; c.font = Font(bold=True, color="FFFFFF")
        for row in ws.iter_rows():
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
                c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        for i, w in enumerate(widths[ws.title]):
            ws.column_dimensions[chr(65 + i)].width = w
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    wb.save(OUT)
    print(f"saved {OUT}: {len(dd)} dictionary rows, {len(dq)} DQ entries")


if __name__ == "__main__":
    main()
