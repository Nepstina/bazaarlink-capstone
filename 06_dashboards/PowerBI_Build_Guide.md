# BazaarLink: Power BI build guide (Day 5)

Goal: `06_dashboards/bazaarlink.pbix` with a star schema, a date table, 8+ DAX measures, a DAX calculated
column, 5+ documented Power Query steps, slicers, drill-through and 3 report pages
(Executive, Delivery, Seller scorecard), plus a Seller detail drill-through page.

Every headline number must match SQL query **SQL-18** within 1% (check list in step 7).

---

## 1. Get the data (choose A or B)

### A. Live from MySQL (best: dashboards reuse the SQL views)
1. Power BI needs **MySQL Connector/NET**, which is not installed yet. Open **MySQL Installer**
   (Start menu) → **Add…** → **MySQL Connectors** → **Connector/NET 8.x** → Next → Execute → Finish.
2. Close and reopen Power BI Desktop.
3. **Home → Get data → More… → MySQL database** → Server `localhost` → Database `bazaarlink` → OK.
   Sign in with **Database** credentials (your MySQL user and password).
4. Tick **vw_order_delivery** and **vw_seller_scorecard** → **Transform Data**.
5. Also load the state list: **Get data → Text/CSV** → `06_dashboards/data/dim_state.csv`.

### B. From CSV (if the connector will not install)
**Get data → Text/CSV**, one at a time, from `06_dashboards/data/`:
`vw_order_delivery.csv`, `vw_seller_scorecard.csv`, `dim_state.csv` → **Transform Data**.
These files are exports of the same three MySQL views (identical logic, checked: revenue 13,221,498.11, on-time 93.23%).

---

## 2. Power Query (Transform Data): rename queries and apply these steps

Rename the queries (right-click → Rename): `vw_order_delivery` → **Fact_Orders**,
`vw_seller_scorecard` → **Dim_Seller**, `dim_state` → **Dim_State**.

After each step, right-click it in **Applied Steps** → **Rename**, using the names in bold
(the brief asks for documented Power Query steps).

**Fact_Orders**
1. **Set data types**: select `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`,
   `order_delivered_customer_date`, `order_estimated_delivery_date` → Data type **Date/Time**;
   `purchase_date` → **Date**; `item_revenue`, `freight_value`, `payment_total`, `delivery_days`,
   `seller_handover_days`, `carrier_days` → **Decimal number**; `delay_days`, `review_score`, `is_*`,
   `n_items`, `max_installments` → **Whole number**.
2. **Replace blank category**: select `primary_category` → Transform → **Replace Values** → find `null`
   (leave "Value To Find" as null) replace with `unknown`.
3. **Replace blank payment type**: `main_payment_type`: replace `null` with `no_payment`.
4. **Add approval days**: Add Column → **Custom Column**, name `approval_days`:
   ```
   if [is_delivery_measurable] = 1 and [order_approved_at] <> null
   then Duration.TotalDays([order_approved_at] - [order_purchase_timestamp]) else null
   ```
   then set its type to Decimal number.
5. **Add instalment band**: Add Column → **Conditional Column**, name `instalment_band`:
   if `max_installments` ≤ 1 → `1 (single)`; else if ≤ 3 → `2-3`; else if ≤ 6 → `4-6`; else `7+`.
6. **Remove unused columns**: right-click `customer_id` and `payment_total` → **Remove**.

**Dim_Seller**
7. **Set data types**: `late_rate`, `negative_review_rate` → Percentage; `revenue`, `freight`, `avg_*` → Decimal.

**Dim_Category** (new dimension from the fact table)
8. Right-click **Fact_Orders** → **Reference** → rename the new query **Dim_Category** →
   right-click `primary_category` → **Remove Other Columns** → Home → **Remove Rows → Remove Duplicates**.

**Close & Apply.**

---

## 3. Date table (DAX)
**Modeling → New table**, paste:
```DAX
Dim_Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2016, 9, 1 ), DATE ( 2018, 10, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month No", MONTH ( [Date] ),
    "Month Key", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM yyyy" ),
    "Weekday", FORMAT ( [Date], "dddd" ),
    "Weekday No", WEEKDAY ( [Date], 2 ),
    "In Trend Window", IF ( [Date] >= DATE ( 2017, 1, 1 ) && [Date] <= DATE ( 2018, 8, 31 ), 1, 0 )
)
```
Then: select the table → **Table tools → Mark as date table** → column `Date`.
Select column `Month` → **Column tools → Sort by column → Month Key**.
Select `Weekday` → **Sort by column → Weekday No**.

---

## 4. Relationships (star schema)
**Model view**: drag to create these (all **Many-to-one**, single direction, fact on the many side):

| From (many) | To (one) |
|---|---|
| Fact_Orders[purchase_date] | Dim_Date[Date] |
| Fact_Orders[customer_state] | Dim_State[state] |
| Fact_Orders[primary_seller_id] | Dim_Seller[seller_id] |
| Fact_Orders[primary_category] | Dim_Category[primary_category] |

Screenshot this view for the README (`06_dashboards/screenshots/pbi_model.png`).

Note for Q&A: the seller link uses the order's first-item seller. Seller KPIs on the scorecard come from
`vw_seller_scorecard`, which counts every seller in multi-seller orders.

---

## 5. Calculated columns (DAX), on Fact_Orders
**Table tools → New column**, one at a time:
```DAX
Delivery Status =
SWITCH (
    TRUE (),
    Fact_Orders[is_delivery_measurable] = 0, "Not delivered",
    Fact_Orders[delay_days] <= 0, "On time",
    "Late"
)
```
```DAX
Delay Bucket Order =
SWITCH ( Fact_Orders[delay_bucket],
    "On time", 1, "1-3 days late", 2, "4-7 days late", 3, "8+ days late", 4, 5 )
```
Select `delay_bucket` → **Sort by column → Delay Bucket Order**.

---

## 6. Measures (DAX)
Create an empty table to hold them: **Home → Enter data** → name `_Measures` → Load.
Then select `_Measures` → **New measure** for each below. Format: % measures as Percentage (1 decimal),
money as Currency/Decimal (2 decimals).

```DAX
Orders = DISTINCTCOUNT ( Fact_Orders[order_id] )
```
```DAX
Delivered Orders = CALCULATE ( [Orders], Fact_Orders[is_delivered] = 1 )
```
```DAX
Revenue = CALCULATE ( SUM ( Fact_Orders[item_revenue] ), Fact_Orders[is_delivered] = 1 )
```
```DAX
AOV = DIVIDE ( [Revenue], [Delivered Orders] )
```
```DAX
Freight = CALCULATE ( SUM ( Fact_Orders[freight_value] ), Fact_Orders[is_delivered] = 1 )
```
```DAX
Freight Ratio % = DIVIDE ( [Freight], [Revenue] )
```
```DAX
Measurable Orders = CALCULATE ( [Orders], Fact_Orders[is_delivery_measurable] = 1 )
```
```DAX
On-time % = DIVIDE ( CALCULATE ( [Orders], Fact_Orders[Delivery Status] = "On time" ), [Measurable Orders] )
```
```DAX
Late % = DIVIDE ( CALCULATE ( [Orders], Fact_Orders[Delivery Status] = "Late" ), [Measurable Orders] )
```
```DAX
On-time Target % = 0.95
```
```DAX
Avg Delivery Days = AVERAGE ( Fact_Orders[delivery_days] )
```
```DAX
Avg Delay Days = AVERAGE ( Fact_Orders[delay_days] )
```
```DAX
Avg Approval Days = AVERAGE ( Fact_Orders[approval_days] )
```
```DAX
Avg Handover Days = AVERAGE ( Fact_Orders[seller_handover_days] )
```
```DAX
Avg Carrier Days = AVERAGE ( Fact_Orders[carrier_days] )
```
```DAX
Avg Review Score = AVERAGE ( Fact_Orders[review_score] )
```
```DAX
Negative Review % = AVERAGE ( Fact_Orders[is_negative_review] )
```
(`is_negative_review` is blank when there is no review, and AVERAGE ignores blanks: reviews scored 1-2 ÷ all reviews.)
```DAX
Customers = DISTINCTCOUNT ( Fact_Orders[customer_unique_id] )
```
```DAX
Repeat Customer % =
VAR PerCustomer =
    ADDCOLUMNS (
        VALUES ( Fact_Orders[customer_unique_id] ),
        "@orders", CALCULATE ( DISTINCTCOUNT ( Fact_Orders[order_id] ) )
    )
RETURN
    DIVIDE ( COUNTROWS ( FILTER ( PerCustomer, [@orders] >= 2 ) ), COUNTROWS ( PerCustomer ) )
```
```DAX
Cancellation % = DIVIDE ( CALCULATE ( [Orders], Fact_Orders[is_cancelled] = 1 ), [Orders] )
```
```DAX
Revenue 3M Rolling Avg =
VAR Last3Months = DATESINPERIOD ( Dim_Date[Date], MAX ( Dim_Date[Date] ), -3, MONTH )
RETURN DIVIDE ( CALCULATE ( [Revenue], Last3Months ), 3 )
```
```DAX
Sellers On Watch List = CALCULATE ( COUNTROWS ( Dim_Seller ), Dim_Seller[watch_status] = "Watch list" )
```

---

## 7. Check the numbers against SQL (do this before building pages)
Put these measures in a **Card (new)** or a **Table** visual with no filters:

| Measure | Must show (SQL-18) |
|---|---|
| Orders | 99,441 |
| Delivered Orders | 96,478 |
| Revenue | 13,221,498.11 |
| AOV | 137.04 |
| Freight Ratio % | 16.6% |
| On-time % | 93.2% |
| Avg Delivery Days | 12.56 |
| Avg Delay Days | -11.88 |
| Avg Review Score | 4.09 |
| Negative Review % | 14.7% |
| Repeat Customer % | 3.1% |
| Cancellation % | 1.2% |

If a number is off, the usual cause is a wrong data type (step 2.1) or a missing relationship. Screenshot this
table for UAT test TC-17 (`06_dashboards/screenshots/pbi_reconciliation.png`).

---

## 8. Report pages
Colours used everywhere: **On time `#1B998B`**, **Late `#C0392B`**, **Navy `#1F3A5F`**.
(View → Themes → Customize current theme → set these as the first colours.)
Every visual title should state the finding, e.g. "On-time % dips at volume peaks", not "On-time % by month".

### Page 1: Executive (COO)
* **Slicers** (top): `Dim_Date[Year]`, `Dim_State[region]`, `Dim_State[state]`.
* **Cards**: Revenue, Orders, AOV, On-time %, Avg Review Score, Repeat Customer %, Cancellation %.
* **Line chart**: X = `Dim_Date[Month]`, Y = `On-time %`. Filters pane → this visual → `In Trend Window` = 1.
  Analytics pane → **Constant line** at 0.95, label "Proposed target 95%".
* **Line and clustered column chart**: X = `Dim_Date[Month]`, columns = Revenue, line = Revenue 3M Rolling Avg
  (same trend-window filter). Title: "Orders peaked in Nov 2017 (Black Friday); 2018 plateaued".
* **Text box**: "Top 3 actions": fill in on Day 6 from the recommendations memo.

### Page 2: Delivery (Logistics Manager, Head of CX)
* **Slicers**: `Dim_Date[Month]`, `Dim_State[region]`, `Dim_Category[primary_category]`.
* **Filled map** (or Map): Location = `Dim_State[state_name]`, add `Dim_State[country]` to Location
  above state so Brazil is found; colour saturation = **Late %**. Title: "Late rate is highest in the North/Northeast".
* **Stacked bar chart**: Y = `Dim_State[state]`, X = Avg Approval Days, Avg Handover Days, Avg Carrier Days.
  Sort by total descending. Title: "The carrier leg is the biggest stage; seller handover adds ~3 days".
* **Clustered column chart**: X = `Fact_Orders[delay_bucket]`, Y = Negative Review %.
  Filter: `delay_bucket` is not "Not delivered". Title: "Even 1-3 days late triples the chance of a bad review".
* **Clustered bar**: Y = `Fact_Orders[route]`, X = Avg Delivery Days (filter route not blank).
  Title: "Inter-state orders take about twice as long".
* **Card**: Avg Delay Days (shows estimates are padded: about -12 days).

### Page 3: Seller scorecard (Seller Success Manager)
* **Slicers**: `Dim_Seller[seller_state]`, `Dim_Seller[watch_status]`.
* **Card**: Sellers On Watch List.
* **Table**: from Dim_Seller: `seller_id`, `seller_state`, `delivered_orders`, `revenue`, `late_rate`,
  `avg_handover_days`, `avg_review_score`, `watch_status`.
  Filters pane → visual → `delivered_orders` **is greater than or equal to 30** (small sellers excluded, per FR-12).
  Sort by `late_rate` descending.
  **Conditional formatting** (right-click column → Conditional formatting → Background colour → Rules):
  `late_rate` ≥ 0.12 → red `#F8D7DA`; `avg_review_score` < 3.8 → red; `watch_status` = "Watch list" → red font.
* **Bar chart**: top 10 sellers by `late_rate` (Filters → Top N = 10 by late_rate, plus delivered_orders ≥ 30).

### Page 4: Seller detail (drill-through)
1. Add a page, name it **Seller detail**.
2. In the Visualizations pane → **Drill through** well → drag `Dim_Seller[seller_id]`. Power BI adds a back button.
3. Visuals: cards for `delivered_orders`, `late_rate`, `avg_handover_days`, `avg_review_score`
   (from Dim_Seller); line chart X = `Dim_Date[Month]`, Y = On-time %; table of
   `Fact_Orders[order_id]`, `purchase_date`, `customer_state`, `delay_days`, `review_score`.
4. Test: on the Seller scorecard page, right-click a seller row → **Drill through → Seller detail**.

Hide the helper columns in Report view (right-click → Hide in report view): `Delay Bucket Order`,
`Month Key`, `Weekday No`.

---

## 9. Save, publish and screenshots
1. **File → Save as** → `06_dashboards/bazaarlink.pbix`.
2. **Home → Publish** → My workspace (needs a Power BI account; if your account cannot publish, submit the
   .pbix plus screenshots, which the brief allows: "published link or screenshots").
3. Screenshot each page into `06_dashboards/screenshots/`: `pbi_executive.png`, `pbi_delivery.png`,
   `pbi_seller_scorecard.png`, `pbi_seller_detail.png`, plus `pbi_model.png` and `pbi_reconciliation.png`.

## 10. Refresh steps (for the BI / IT Lead handover)
* Source A (MySQL): Home → **Refresh**. Credentials: File → Options and settings → Data source settings.
* Source B (CSV): re-run `05_python/src/clean_data.py`, re-run the SQL scripts, re-export the views to
  `06_dashboards/data/`, then Home → **Refresh**.
* After every refresh, re-check the step 7 table against SQL-18.
