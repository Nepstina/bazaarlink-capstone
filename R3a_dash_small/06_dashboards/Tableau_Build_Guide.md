# BazaarLink: Tableau build guide (Day 6)

Goal (brief): **4+ sheets in one interactive dashboard, with a map and filter actions, published to Tableau Public.**
Data: `06_dashboards/data/tableau_orders.csv` (one row per order, exported from the MySQL view
`vw_order_delivery` plus state names and regions; revenue 13,221,498.11 and on-time 93.23%, same as SQL-18).

---

## 1. Connect
1. Open **Tableau** → under **Connect → To a File** click **Text file**.
2. Pick `06_dashboards/data/tableau_orders.csv` → it opens the Data Source page.
3. Check the type icons above the columns (click an icon to change it):
   * `purchase_date` → **Date** (calendar icon)
   * `state_name` → globe icon: **Geographic Role → State/Province**
   * `country` → **Geographic Role → Country/Region**
   * `customer_state`, `order_status`, `delivery_status`, `delay_bucket`, `primary_category`, `route`, `region` → **String**
   * all the `is_…` columns, `item_revenue`, `delivery_days`, `delay_days`, `review_score` → **Number**
4. Click **Sheet 1** (bottom left) to start building.

## 2. Calculated fields (same KPI rules as SQL, Python and Power BI)
In the Data pane: **Analysis → Create Calculated Field…**, type the name, paste the formula, OK.

| Name | Formula |
|---|---|
| Orders | `COUNTD([order_id])` |
| Revenue | `SUM(IF [is_delivered] = 1 THEN [item_revenue] END)` |
| On-time % | `SUM([is_on_time]) / SUM([is_delivery_measurable])` |
| Late % | `SUM([is_late]) / SUM([is_delivery_measurable])` |
| Negative Review % | `AVG([is_negative_review])` |
| Avg Review Score | `AVG([review_score])` |
| Avg Delivery Days | `AVG([delivery_days])` |

Right-click **On-time %**, **Late %**, **Negative Review %** → **Default Properties → Number Format → Percentage, 1 decimal**.
Right-click **Revenue** → Default Properties → Number Format → **Currency (Custom)**, prefix `R$ `, display units Millions.

**Check:** drag **On-time %** onto the empty sheet → it must show **93.2%**. (Then clear the sheet: toolbar ✖ Clear Sheet.)

## 3. The four sheets
Rename each sheet by double-clicking its tab at the bottom. A new sheet: the small icon right of the last tab.

### Sheet 1: "Late rate map"
1. Double-click **state_name** → Tableau draws a map with dots.
   * If it says "unknown locations": **Map → Edit Locations → Country/Region: Brazil**.
2. In the **Marks** card, change the dropdown from Automatic to **Map** (filled map).
3. Drag **Late %** onto **Color**. Click Color → Edit Colors → **Red** (or Orange-Blue Diverging, reversed).
4. Drag **Orders** and **Avg Delivery Days** onto **Tooltip**.
5. Title (double-click the title): `Late rate by customer state: worst in the Northeast (AL, MA, SE)`

### Sheet 2: "Category view"
1. Drag **primary_category** to **Rows**, **Revenue** to **Columns**.
2. Toolbar → **Sort descending**.
3. Drag **primary_category** to **Filters** → **Top** tab → **By field: Top 15 by Revenue** → OK.
4. Drag **Late %** onto **Color** (red = higher late rate).
5. Drag **Revenue** onto **Label**.
6. Title: `Top 15 categories by revenue, coloured by late rate`

### Sheet 3: "Delay vs review"
1. Drag **delay_bucket** to **Columns**, **Negative Review %** to **Rows**.
2. Drag **delay_bucket** to **Filters** → untick **Not delivered**.
3. Put the bars in order: right-click the `delay_bucket` pill on Columns → **Sort → Manual**:
   On time, 1-3 days late, 4-7 days late, 8+ days late.
4. Drag **Negative Review %** onto **Label**. Drag **delay_bucket** onto **Color**.
5. Title: `Even 1-3 days late triples the chance of a 1-2 star review`
   (Expected: about 9% on time, 32%, 68%, 79%.)

### Sheet 4: "On-time trend"
1. Right-click-drag **purchase_date** to **Columns** → choose **MONTH(purchase_date)** (the green, continuous one).
2. Drag **On-time %** to **Rows** → line chart.
3. Drag **purchase_date** to **Filters** → **Range of dates** → 01/01/2017 to 31/08/2018 → OK.
4. Reference line: **Analytics** pane (top left tab) → drag **Reference Line** onto the chart → **Table** →
   Value: **Constant 0.95**, Label: Custom `Target 95%` → OK.
5. Title: `On-time % dips below the 95% target at volume peaks (Nov-17, Feb-Mar-18)`

(Optional Sheet 5 "Route": **route** on Rows, **Avg Delivery Days** on Columns, filter out Null.)

## 4. The dashboard
1. Click the **New Dashboard** icon (bottom, the grid icon next to the new sheet icon).
2. Left panel → **Size → Automatic** (or Fixed 1200 × 850).
3. Drag the sheets in: **Late rate map** on the left (large), **On-time trend** top right,
   **Delay vs review** and **Category view** below it.
4. Tick **Show dashboard title** (Dashboard menu) → `BazaarLink: delivery performance and customer satisfaction`.

### Filter action (required)
1. **Dashboard → Actions… → Add Action → Filter…**
2. Name: `Filter by state`
   * Source sheets: **Late rate map** only
   * Run action on: **Select**
   * Target sheets: **Category view, Delay vs review, On-time trend**
   * Clearing the selection will: **Show all values**
3. OK → OK.
4. **Test:** click **Alagoas (AL)** on the map → the other three charts change to Alagoas only.
   Click empty map space → everything returns.

(Quick alternative: select the map on the dashboard → click the **funnel icon "Use as Filter"** on its border.)

Add a second action if you like: Source **Category view** → Targets **Late rate map** (click a category to see where it is late).

## 5. Publish to Tableau Public
1. **File → Save to Tableau Public As…** (in Tableau Desktop: **Server → Tableau Public → Save to Tableau Public…**).
2. Sign in with your free Tableau Public account (create one at public.tableau.com if needed).
3. Name: `BazaarLink Delivery Performance` → Save. It opens in the browser.
4. Copy the browser link into `06_dashboards/tableau_link.md`.
5. Screenshot the dashboard → `06_dashboards/screenshots/tableau_dashboard.png`.

Tableau Public is public: the data is the anonymised Olist dataset, which is allowed (BRD constraint C-03).

## 6. Q&A notes
* Map uses Tableau's built-in geocoding for Brazilian states (`state_name` with accents, country = Brazil).
* KPI formulas match SQL-18: on-time 93.2%, negative review 14.7%.
* The map shows the North (AM, RR, AP) is rarely *late* even though deliveries take longest: their promised
  dates are longer. The real late-delivery problem is the Northeast.
