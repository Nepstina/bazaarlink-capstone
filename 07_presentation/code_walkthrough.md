# Code walkthrough: explain your SQL and Python in plain words

Study this with the files open. For each part, close this page and explain it aloud in your own words.
If you can do that, you're ready for "go through your script".

---

## Part A: SQL (04_sql)

### The 4 files, in the order they run
| File | One sentence |
|---|---|
| 01_schema.sql | Creates the database and 7 empty tables, with primary keys (unique ID per row) and foreign keys (links between tables). |
| 02_load.sql | Copies the cleaned CSV files into those tables. Blank values become NULL. |
| 04_views.sql | Saves 3 ready-made queries (views) that Power BI and Tableau reuse, so every tool uses the same logic. |
| 03_analysis.sql | 25 queries, each answering one business question (Q1-Q13). |

### The 6 SQL ideas that repeat everywhere (learn these and you can read every query)
1. **WHERE order_status = 'delivered'**: keep only delivered orders. Revenue and delivery KPIs use delivered orders only.
2. **DATEDIFF(delivered, estimated)**: days between two dates. 0 or negative = on time, positive = late.
3. **CASE WHEN … THEN 1 ELSE 0 END**: turns a yes/no into 1/0. `AVG` of 1/0 gives a percentage (e.g. late rate).
4. **JOIN**: connects tables by their shared ID. INNER JOIN keeps only matches; LEFT JOIN keeps everything from the left table even with no match (e.g. orders with no review).
5. **GROUP BY … HAVING**: one row per group (per state, per month). HAVING filters groups, e.g. `HAVING COUNT(*) >= 30` keeps states or sellers with at least 30 orders.
6. **Subquery / CTE (WITH …)**: a small query inside a bigger one. A CTE gives it a name so the main query is easier to read.

### The queries markers are most likely to point at
| Query | What it does, in one line |
|---|---|
| SQL-01 | Monthly orders and revenue. Items are added up per order first (subquery), then joined to orders, so revenue isn't counted twice. A window function makes the 3-month average. |
| SQL-03 | Revenue per state, plus each state's % of total (the total comes from a small subquery). |
| SQL-05 | On-time % per month: CASE marks each order on time (1) or late (0), and AVG gives the %. |
| SQL-06 | Delivery days and late % per customer state, only states with 30+ orders (HAVING). |
| SQL-08 | Days spent in each stage: approval, seller handover, carrier. Stages with impossible dates are skipped. |
| SQL-10 | Average review for late vs on-time orders. LEFT JOIN keeps orders without a review. |
| SQL-11 | % of negative reviews in each delay bucket (on time, 1-3, 4-7, 8+ days late). |
| SQL-13 | Repeat customer rate: counts orders per customer_unique_id in a subquery, then the % with 2 or more. |
| SQL-15 | Seller watch list: sellers with 30+ orders AND (late ≥ 12% OR review < 3.8). |
| SQL-18 | All headline KPIs in one row: used to check Python, Power BI and Tableau match. |

### Views
* **vw_order_delivery**: one row per order with everything the dashboards need (delivery days, delay bucket, revenue, review). Items and payments are summed per order *before* joining, so nothing is double counted.
* **vw_seller_scorecard**: one row per seller: orders, late rate, handover days, review, watch status.
* **vw_monthly_kpis**: one row per month, built on vw_order_delivery.

---

## Part B: Python (05_python)

### Files
| File | One sentence |
|---|---|
| src/clean_data.py | Reads the raw CSVs, fixes data problems, adds delivery columns, saves cleaned CSVs and writes the data quality log. |
| src/loader.py | Loads cleaned CSVs and checks required columns exist; if not, raises my own error (MissingColumnError). |
| src/analysis.py | All calculations: KPIs, hypothesis tests, probability, regression, retention, CR-01, JSON export. |
| eda.ipynb | The story: runs analysis.py step by step with charts and written findings (sections 1-11). |
| kpi_summary.json | The headline KPIs and test results saved as a file. |

### Cleaning decisions (clean_data.py), the "why" questions
* **Kept outliers, only flagged them**: long deliveries are the business problem; deleting them would hide lateness.
* **Latest review per order**: some orders had 2 reviews; the latest is the customer's final opinion.
* **customer_unique_id**: customer_id changes every order; otherwise repeat customers look like 0%.
* **Compared dates, not times, for on-time**: the promised date has no time of day.
* **Impossible stage dates set to blank**: e.g. carrier pickup before payment approval (1,325 orders).

### Programming concepts the brief asks for, and where they are
| Concept | Where | Say it like this |
|---|---|---|
| Class + inheritance | `CleanDataLoader(BaseLoader)`, `OrdersAnalyser(BaseAnalyser)` | "The child class reuses the parent's code and adds its own methods." |
| Encapsulation | `self._df` with a `data` property | "The data is kept private; outside code gets a copy, so it can't change it by accident." |
| Custom exception | `MissingColumnError` in loader.py | "If a file is missing a column, my own error says exactly which one." |
| try / except / finally | `read_csv` in loader.py | "Try to load; on error, log it; finally, always record the attempt." |
| os and datetime | paths, timestamps in logs and JSON | "os builds file paths; datetime stamps when things ran." |

### Statistics, in one line each
* **Mann-Whitney U**: compares two groups' review scores without assuming a normal distribution (scores are 1-5 and skewed). p < 0.001 means the gap is almost certainly not chance.
* **Welch t-test**: a second check comparing averages; it agrees.
* **Chi-square**: tests whether two yes/no things are linked (late? and negative review?). They are.
* **Conditional probability**: P(negative | late) = 62% vs P(negative | on time) = 9%, which is 6.7 times higher.
* **Regression**: estimates how much each factor adds to delivery days (inter-state +6.9 days; each handover day about +1 day). R² 0.28 = it explains 28%; the rest is missing data such as distance and carrier.
* **Section 11 what-if**: "If we change one thing (e.g. cap handover at 3 days), how many late orders become on time?"

---

## Part C: 15 likely questions, with short answers
1. **Why aggregate items before joining payments or reviews?** One order can have 3 items; joining first repeats the review 3 times and inflates the totals.
2. **INNER vs LEFT JOIN?** INNER keeps only matches; LEFT keeps every order even without a review.
3. **What is a view and why use it?** A saved query; dashboards reuse it, so the logic is written once.
4. **What does HAVING do that WHERE can't?** WHERE filters rows before grouping; HAVING filters groups after.
5. **Why CASE inside AVG?** CASE makes 1/0; the average of 1s and 0s is a percentage.
6. **What's a primary key and a foreign key?** A primary key is a unique ID per row; a foreign key points to another table's ID, so invalid links can't exist.
7. **Why is revenue different from payment totals?** Payments include freight and instalment interest; revenue is item price only.
8. **How did you check the numbers were right?** SQL-18 vs Python (kpi_summary.json) vs Power BI KPI Check page: identical.
9. **Why Mann-Whitney, not a t-test?** Review scores are ordinal and skewed; Mann-Whitney doesn't need normal data.
10. **What does p < 0.001 mean?** If lateness made no difference, a gap this big would almost never happen by chance.
11. **Does lateness cause bad reviews?** Strongly linked; I don't claim proven cause because other problems can come with late orders.
12. **What does R² = 0.28 mean?** The model explains 28% of the variation in delivery time.
13. **Where is inheritance in your code?** OrdersAnalyser inherits from BaseAnalyser and reuses describe() and require().
14. **What happens if a column is missing?** loader.py raises MissingColumnError naming the column; the notebook shows a demo.
15. **How did you size the recommendations?** What-if scenarios in notebook section 11: change one driver, recount late orders.

---

## How to study (1 hour)
1. Open `04_sql/03_analysis.sql` next to Part A. Read 5 queries and say each aloud in one sentence.
2. Open `05_python/src/analysis.py`. Find each concept in the table above.
3. Cover the answers in Part C and answer each question aloud.
4. Rewrite a few code comments in your own words where it helps you remember (only for parts you understand).
