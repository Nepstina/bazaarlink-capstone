# Confluence space: BazaarLink Analytics (page drafts)

Create a space called **BazaarLink Analytics**, then one page per section below
(+ Create → Page → paste). Upload the files named in each page as attachments.
Items in [brackets] are for you to fill in with what really happened.

Page tree:
1. Home (project overview)
2. Business Requirements (BRD)
3. Data dictionary and data quality log
4. Meeting notes: stakeholder interviews
5. Decision log
6. Change log
7. Sprint 1 review and retrospective
8. Sprint 2 review and retrospective
9. UAT results
10. Recommendations
11. Dashboard handover and refresh steps

---

## 1. Home
**Project:** Delivering on the Promise: delivery performance and customer satisfaction analysis
**Client (fictional):** BazaarLink · **Sponsor:** COO · **Dates:** 3-10 Nov 2026
**Goal:** one trusted view of orders, deliveries, reviews and revenue; quantify the cost of late delivery; prioritised, sized recommendations.
**Links:** GitHub [link] · Jira [link] · Power BI [link or screenshots] · Tableau Public [link]

Headline numbers (agree across SQL, Python, Power BI, Tableau):
on-time 93.2% · avg delivery 12.6 days · avg review 4.09 · negative reviews 14.7% · repeat customers 3.1% · revenue R$ 13.22M.

## 2. Business Requirements
Attach `01_business_docs/BRD_v1_BazaarLink.docx` and the RTM workbook. Summary: 16 functional and 6 non-functional
requirements, 13 KPI definitions, 13 business questions; all traced in the RTM to a query, a visual and a test case.

## 3. Data dictionary and data quality log
Attach `02_data/data_dictionary_and_dq_log.xlsx`. Summary: 9 source files cleaned; 48 data quality issues logged with
action and reason; row counts reconciled (only reviews changed: 551 duplicate reviews removed, latest kept).

## 4. Meeting notes: stakeholder interviews (Day 1)
| Stakeholder | Date | Key points / hidden requirement captured |
|---|---|---|
| COO | [date] | Wants one headline on-time % with monthly trend and a target for next year → FR-04, 95% target line |
| Head of CX | [date] | Negative = score 1-2; reviews split by delay bucket (on time, 1-3, 4-7, 8+) → FR-09 |
| Logistics Manager | [date] | "Carriers are the problem"; wants delay by stage → FR-06 (data shows carrier leg largest, handover controllable) |
| Seller Success Manager | [date] | Watch list only for sellers with 30+ orders → FR-12 |
| Finance Controller | [date] | Revenue excludes freight, delivered only; explain payment vs item totals → BR-04 |
| BI / IT Lead | [date] | Refresh steps and access rules → NFR-04, NFR-05 |
[Edit to match what was actually said in your interviews.]

## 5. Decision log
| # | Date | Decision | Reason | Approved by |
|---|---|---|---|---|
| D-01 | 06 Nov | KPI definitions per BRD section 7 are the single source | Teams used different numbers | COO |
| D-02 | 06 Nov | On-time compares calendar dates (delivered date ≤ estimated date) | Estimated date has no time; same rule as SQL DATEDIFF | Analytics team |
| D-03 | 06 Nov | Keep the latest review when an order has several | Order-level averages; latest = final opinion | Head of CX |
| D-04 | 06 Nov | Flag IQR outliers, do not remove them | Long deliveries are the business problem | Analytics team |
| D-05 | 06 Nov | Trend window Jan 2017 - Aug 2018 | Other months have < 1,000 orders | Analytics team |
| D-06 | 07 Nov | Watch list = 30+ orders and late ≥ 12% or review < 3.8 | 12% ≈ double the platform late rate | Seller Success Manager |
| D-07 | 07 Nov | Power BI loads CSV exports of the MySQL views | MySQL connector not installed; same view logic | BI / IT Lead |
| D-08 | 07 Nov | CR-01 instalment analysis approved | Low effort, no KPI change | COO |
| D-09 | 07 Nov | Seller and category on order level = first item in the order | One value per order needed; scorecard uses all items | Analytics team |

## 6. Change log
| CR | Date | Request | Impact | Decision |
|---|---|---|---|---|
| CR-01 | 07 Nov | Finance: instalments vs AOV and cancellations | +1 notebook section, +1 SQL query, ~1 hour, no KPI change | Approved; delivered (AOV R$ 100 → R$ 301; cancellations flat) |
Full impact analysis: `01_business_docs/change_management_plan.md` appendix.

## 7. Sprint 1 review and retrospective (3-7 Nov)
**Sprint goal:** requirements, data cleaning, Excel dashboard, SQL analysis and views.
**Completed:** BRD, discovery pack, RTM, Jira backlog; cleaning script and data quality log; Excel quick-look; SQL schema,
load, 25 queries and 3 views reconciled with Pandas.
**Carried over to Sprint 2:** dashboard visuals and UAT sub-tasks of US-03, 04, 06, 07, 12 (analysis done, visuals pending).
**Retrospective**
* Went well: KPI definitions agreed first, so SQL and Python matched exactly.
* Didn't go well: two raw files were missing at first; LOAD DATA was blocked until local_infile was enabled.
* Improve: estimate dashboard work separately from analysis work; check tool setup (connectors) on day 1.

## 8. Sprint 2 review and retrospective (8-10 Nov)
**Sprint goal:** Python statistics, Power BI, Tableau, recommendations, UAT, presentation.
**Completed:** EDA notebook with 3 hypothesis tests and regression; Power BI (5 pages, drill-through); Tableau dashboard
with map and filter action; recommendations memo; UAT pack; CR-01. [Add: deck, README, final UAT sign-off.]
**Retrospective**
* Went well: every dashboard reconciled to SQL-18 before building pages.
* Didn't go well: Power BI measures were created in the wrong table / edited by mistake (DEF-04).
* Improve: build a KPI check page first in every BI tool (we did, and it caught errors early).
[Add burndown chart screenshot.]

## 9. UAT results
Attach the RTM workbook (Test Cases, Defect Log, UAT Sign-off sheets). Summary: 22 test cases; 20 passed in analyst
self-test, 2 (performance, usability) for the peer team; 9 defects found and fixed (1 workaround). [Add peer team results and sign-off.]

## 10. Recommendations
Paste `01_business_docs/recommendations_memo.md`.

## 11. Dashboard handover and refresh steps
Paste section 10 of `06_dashboards/PowerBI_Build_Guide.md`. Access: Power BI workspace members = COO, CX, Logistics,
Seller Success, Finance; Tableau Public uses anonymised data only.
