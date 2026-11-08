# AI use log

The brief allows AI use if it is logged, and says AI may draft and summarise but never supply numbers.
Every number in this project comes from a SQL query, a notebook cell or a DAX measure, and the headline KPIs were
reconciled across SQL, Python, Excel, Power BI and Tableau (UAT TC-17).

| # | Date | Tool | Purpose | What AI produced | What I checked / changed by hand |
|---|---|---|---|---|---|
| 1 | 06 Nov | Claude (Claude Code) | Understand the brief, plan the 7 days | Plan and checklist of deliverables | Adjusted the plan to my timeline and sprint dates |
| 2 | 06 Nov | Claude | Day 1 BA documents | Drafts of BRD, discovery pack (SWOT, gap analysis, As-Is), RTM, user stories, Jira import CSV | [Reviewed against the brief; edited stakeholder notes, sprint dates, author details] |
| 3 | 06 Nov | Claude | Data cleaning | `clean_data.py`, data dictionary builder, data quality log | Ran the script; checked row counts and each logged issue; confirmed repeat rate 3.1% matches the brief's hint |
| 4 | 06-07 Nov | Claude | Excel quick-look | Workbook build script (formulas, validation, pivot, slicers) | Opened in Excel; tested the state and year filters; checked KPIs against SQL |
| 5 | 07 Nov | Claude | SQL | Schema, load, 25 queries, 3 views, runner script | Ran every script in MySQL Workbench myself; fixed loading setup (local_infile); checked results against Python |
| 6 | 07 Nov | Claude | Python module and EDA notebook | `loader.py`, `analysis.py`, `eda.ipynb` with tests and findings | Ran the notebook/script myself; read and can explain each test, p-value and the regression limits |
| 7 | 07 Nov | Claude | Power BI and Tableau | Step-by-step build guides and DAX / calculated-field formulas | Built every page, measure, relationship and visual myself; fixed defects DEF-01 to DEF-09; checked numbers on a KPI Check page |
| 8 | 07 Nov | Claude | Recommendations and sizing | Memo draft and what-if sizing code (notebook section 11) | Checked each sized number in the notebook output; reviewed wording to avoid claiming causation |
| 9 | 07 Nov | Claude | Documentation | Change management plan, Confluence page drafts, UAT pack updates, README, deck outline | [Reviewed and edited before publishing; filled in interview notes and links] |
| 10 | [date] | Gamma | Slide deck | Slide layout from my outline | [Checked every number on every slide against the notebook / SQL] |

**What I did not use AI for:** deciding the final recommendations to present, the interview conversations, the UAT by
the peer team, and the presentation itself.

**Lessons:** AI was fastest for boilerplate (schemas, documentation structure); every output still needed checking
in the real tools: several defects (Power BI measure placement, Tableau geographic roles) only showed up when I built them.
