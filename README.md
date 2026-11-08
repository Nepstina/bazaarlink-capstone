# BazaarLink: Delivering on the Promise
### Delivery performance and customer satisfaction analytics (capstone project)

BazaarLink, an online marketplace for small sellers in Brazil, did not know how much late delivery was costing it in
reviews and repeat business, or where to act first. This project builds one trusted view of orders, deliveries, reviews
and revenue, quantifies the link between delivery and satisfaction, finds the root causes, and recommends sized actions.

**Data:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce): 9 linked CSV files, 99,441 orders, 2016-2018.
**Tools:** Excel, MySQL 8, Python (Pandas, NumPy, SciPy, Matplotlib, Seaborn), Power BI, Tableau, Jira, Confluence, Miro, Gamma.

## Links
| Deliverable | Link |
|---|---|
| Tableau Public dashboard | https://public.tableau.com/app/profile/nepstina.s/viz/bazaarlink_tableau_public/Dashboard |
| Power BI | `06_dashboards/bazaarlink.pbix` + screenshots in `06_dashboards/screenshots/` |
| Jira board | https://nepstina1323-1793988703125.atlassian.net/jira/software/projects/SCRUM/boards/1 |
| Confluence space | https://nepstina1323-1793988703125.atlassian.net/wiki/spaces/BA |
| Final deck | `07_presentation/final_deck.pdf` |
| GitHub repository | https://github.com/Nepstina/bazaarlink-capstone |
| Miro board (stakeholder map, SWOT, As-Is / To-Be) | https://miro.com/app/board/uXjVEQDl3VI=/ · PDF: `01_business_docs/miro_discovery_and_process_maps.pdf` |

## Key findings
| # | Finding | Evidence |
|---|---|---|
| 1 | On-time delivery is **93.2%**, but falls to **81-88%** in peak months (Nov-17 Black Friday, Feb-Mar-18) | SQL-05, Power BI Executive |
| 2 | Late orders average **2.27 stars vs 4.29** on time (Mann-Whitney p < 0.001); a late order is **6.7×** as likely to get a 1-2 star review | eda.ipynb s5-6, SQL-10/11 |
| 3 | There is no safe lateness: negative-review probability is 9% on time, **32%** at 1-3 days late, 68% at 4-7, **79%** at 8+ | SQL-11, Tableau, Power BI Delivery |
| 4 | Inter-state orders take **15.1 vs 7.9 days**; inter-state adds **6.9 days** holding other factors constant | SQL-12, regression |
| 5 | Each extra day of seller handover adds about **1 delivery day**; **110 sellers** are on the watch list | Regression (R² 0.28), SQL-15, Power BI Seller scorecard |
| 6 | Estimates are padded (23.7 days promised vs 12.6 actual), yet a blanket 3-day cut would drop on-time to ~89% | SQL-09b, eda.ipynb s11 |
| 7 | Only **3.1%** of 96,096 customers order twice; 2.54% after a late first order vs 3.13% after on-time | SQL-13/14 |

## Recommendations (sized)
1. **Peak-season capacity plan** (Nov, Feb-Mar): meeting 95% in peak months → on-time **93.2% → 95.6%**, ~1,200 fewer bad reviews.
2. **Seller handover rule ≤ 3 days**: on-time **→ 94.6%** (+1.3 pts), ~680 fewer bad reviews.
3. **Seller watch-list programme** (110 sellers): on-time **→ 93.9%**, ~350 fewer bad reviews.
4. **Route-based delivery estimates**: pilot only (a blanket cut hurts on-time).

Full memo: `01_business_docs/recommendations_memo.md`.

## Approach
1. **Requirements:** BRD with 16 functional and 6 non-functional requirements, 13 KPI definitions, user stories with Given/When/Then, RTM.
2. **Data cleaning:** `05_python/src/clean_data.py`: types, missing values, duplicates, IQR outliers flagged (not removed), derived delivery columns; 48 issues in the data quality log.
3. **SQL:** schema with primary and foreign keys, 25 analysis queries, 3 views reused by dashboards.
4. **Python EDA:** reusable module (`loader.py`, `analysis.py`) + `eda.ipynb`: descriptive statistics, Mann-Whitney and chi-square tests, conditional probability, correlation and regression, change request CR-01.
5. **Dashboards:** Excel quick-look (Finance), Power BI (Executive, Delivery, Seller scorecard + drill-through), Tableau (state map with filter actions).
6. **UAT:** 22 test cases, defect log, sign-off sheet (RTM workbook).

One KPI definition set is used everywhere: SQL, Python, Excel, Power BI and Tableau headline numbers match exactly (UAT TC-17).

## Repository structure
```
01_business_docs/   BRD, discovery pack, RTM (+ UAT, defects, change log), memo, To-Be map, change plan, Confluence drafts
02_data/            data dictionary + DQ log, logs/, cleaned/  (raw/ not committed; CSV files over 5 MB are zipped: unzip before use)
03_excel/           finance_quicklook.xlsx
04_sql/             01_schema.sql, 02_load.sql, 03_analysis.sql, 04_views.sql, run_sql.py
05_python/          src/ (clean_data.py, loader.py, analysis.py, ...), eda.ipynb, eda.py, kpi_summary.json, figures/
06_dashboards/      bazaarlink.pbix, bazaarlink_tableau.twbx, tableau_link.md, data/, screenshots/, build guides
07_presentation/    final_deck.pdf, ai_use_log.md, deck_outline.md
```

## How to reproduce
1. Download the 9 Olist CSVs from Kaggle into `02_data/raw/` (not committed: see `.gitignore`).
2. `pip install pandas numpy scipy matplotlib seaborn openpyxl mysql-connector-python`
3. `python 05_python/src/clean_data.py` → cleaned CSVs and data quality log.
4. `python 04_sql/run_sql.py --user root` → MySQL schema, load, views, all queries and reconciliation.
5. Open `05_python/eda.ipynb` and Run All (or `python 05_python/eda.py`).
6. Open the `.pbix` / `.twbx` files and refresh.

## Screenshots
Power BI: `06_dashboards/screenshots/pbi_executive.png`, `pbi_delivery.png`, `pbi_seller_scorecard.png`, `pbi_model.png`.
Tableau: `06_dashboards/screenshots/tableau_dashboard.png`. Excel: `06_dashboards/screenshots/excel_quicklook.png`.

## Limits
Observational data (associations, not proven causes); 2016-2018 only; no distance or carrier identity; regression explains 28% of delivery time.

## AI use
AI assistance was used and is logged in `07_presentation/ai_use_log.md`. AI never supplied numbers: every number comes from a SQL query, a notebook cell or a DAX measure.

## Resume bullets
* Built an end-to-end delivery analytics solution on 99k e-commerce orders (Excel, MySQL, Python, Power BI, Tableau) with one KPI definition set reconciled to 0% difference across all tools.
* Proved late deliveries are 6.7× more likely to receive 1-2 star reviews (Mann-Whitney, chi-square) and identified seller handover and peak capacity as controllable root causes.
* Delivered sized recommendations projected to lift on-time delivery from 93.2% to 95.6% and cut ~1,200 negative reviews; documented with BRD, RTM, UAT and change management.

[Author: your name] · [LinkedIn] · [date]
