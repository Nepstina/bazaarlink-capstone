# Change management plan: rolling out the new delivery KPIs

## 1. What is changing
* One agreed set of KPI definitions (BRD section 7) replaces each team's own spreadsheet numbers.
* Three dashboards become the single source: Power BI (Executive, Delivery, Seller scorecard), Tableau (state map), Excel quick-look (Finance).
* New targets: on-time ≥ 95% every month, seller handover ≤ 3 days, negative review rate ≤ 12%.
* New seller policy: weekly scorecard and watch list (30+ orders and late ≥ 12% or review < 3.8).

## 2. Impact by stakeholder

| Stakeholder | What changes for them | Likely concern | Response |
|---|---|---|---|
| COO | Uses Executive page monthly; owns targets | "Are these numbers trustworthy?" | Reconciliation: SQL, Python, Power BI and Tableau agree to 0% difference (UAT TC-17) |
| Head of CX | Negative review % by delay bucket replaces anecdotes | Reviews also depend on product quality | Show association, not causation; tag reviews by delay bucket |
| Logistics Manager | Delay split by stage; peak-season plan | "Carriers are the problem" | Data shows the carrier leg is largest, but handover and peaks are controllable |
| Seller Success Manager | Owns the watch list and handover rule | Fairness to small sellers | Only sellers with 30+ orders are judged |
| Finance Controller | Revenue = item price of delivered orders, no freight | Payment totals will not match | Documented: payments include freight and instalment interest |
| BI / IT Lead | Runs refresh after handover | Workload | Documented refresh steps (PowerBI_Build_Guide.md section 10) |
| Sellers | Handover rule and possible penalties | Resistance | 4-week warning period, alerts on day 2, coaching before penalties |

## 3. Rollout plan (ADKAR-based)

| Phase | When | Activities | Success measure |
|---|---|---|---|
| Awareness | Week 1 | COO announces the single KPI set; share the recommendations memo | All teams received memo |
| Desire | Week 1-2 | Show each team "their" page; agree targets with owners | Owners confirm targets |
| Knowledge | Week 2 | 45-minute dashboard training per team; KPI dictionary on Confluence | Attendance ≥ 90% |
| Ability | Week 3-4 | Teams use dashboards in weekly meetings; old spreadsheets read-only | Old spreadsheets retired |
| Reinforcement | Month 2+ | Monthly KPI review with COO; seller scorecard reviewed weekly | On-time trend, watch-list size, adoption (dashboard views) |

## 4. Communication plan
| Audience | Message | Channel | Frequency |
|---|---|---|---|
| Leadership | KPIs vs targets, top 3 actions | Executive page + monthly review | Monthly |
| Operations teams | Stage delays, peak readiness | Delivery page, stand-up | Weekly |
| Sellers | Handover rule, own performance | Seller portal email | Weekly from rollout |
| All staff | One KPI definition set | Confluence page | Once + on change |

## 5. Change control for KPI definitions
Any change to a KPI follows the BRD change-control process: log a change request → impact analysis (SQL, Python, Power BI, Tableau, Excel) → sponsor approval → update BRD, RTM and Confluence → re-run reconciliation.

## 6. Risks
| Risk | Mitigation |
|---|---|
| Teams keep using old spreadsheets | Make old files read-only after week 4 |
| Sellers resist the handover rule | Warning period, coaching, publish the evidence |
| Numbers drift after refresh | Re-run the KPI Check page against SQL-18 after every refresh |

---

## Appendix: change request CR-01 impact analysis

| Item | Detail |
|---|---|
| Request | Finance (Day 4): "Do orders paid in more instalments have a higher AOV or more cancellations?" |
| Logged | RTM Change Log sheet, CR-01, 2026-11-07 |
| Scope impact | +1 notebook section (eda.ipynb section 9), +1 SQL query (SQL-04b), Excel chart already present (AOV by instalments), Power BI instalment_band column |
| Time impact | About 1 hour; no change to sprint goal |
| KPI impact | None: no definition changes |
| Documents updated | BRD (FR-03 note), RTM, Jira US-05 |
| Approval | Sponsor (COO) approval recorded in the Confluence decision log |
| Result | AOV rises from R$ 100 (single payment) to R$ 301 (7+ instalments); cancellation rate flat at 1.1-1.4% |
