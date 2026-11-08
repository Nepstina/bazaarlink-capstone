# Recommendations memo: delivering on the promise

**To:** Chief Operating Officer (sponsor) · **Cc:** Head of Customer Experience, Logistics Manager, Seller Success Manager, Finance Controller
**From:** BazaarLink analytics team · **Date:** [date] · **Data:** Olist orders Sep 2016 – Oct 2018 (99,441 orders; delivery KPIs on 96,470 measurable delivered orders)

## Situation
* On-time delivery is **93.2%** overall, but it falls sharply at volume peaks: **87.6%** in Nov 2017 (Black Friday), **85.9%** in Feb 2018 and **81.0%** in Mar 2018.
* Late delivery is strongly associated with bad reviews: late orders average **2.27 stars** against **4.29** on time (Mann-Whitney p < 0.001). A late order is **6.7×** as likely to get a 1-2 star review (62.4% vs 9.3%).
* Only **3.1%** of customers order twice, and fewer still after a late first order (2.54% vs 3.13%, significant but small effect).

## Root causes (not symptoms)
1. **Peak-season capacity:** the late rate spikes when order volume spikes; the system has no peak buffer.
2. **Inter-state shipping:** inter-state orders take **15.1 days** vs **7.9** same-state; holding other factors constant, inter-state adds **6.9 days** (regression).
3. **Seller handover:** sellers hold orders **2.9 days** on average; each extra handover day adds about **1.05 delivery days** (regression, R² 0.28).
4. **A concentrated group of sellers:** **110 sellers** with 30+ orders have a late rate of 12%+ or an average review below 3.8. Their orders (11.2% of volume) are late **12.2%** of the time vs **6.1%** for everyone else.
5. **Carrier leg:** 9.3 of the 12.6 delivery days are with the carrier; longest to remote North/Northeast states.

## Recommendations (prioritised)

| # | Action | KPI it moves | Sized impact (from the data) | Owner |
|---|---|---|---|---|
| 1 | **Peak-season plan**: pre-book extra carrier capacity and set seller stock targets for Nov (Black Friday) and Feb-Mar | On-time %, Negative review % | If the 4 peak months (Nov-17, Dec-17, Feb-18, Mar-18, 26,359 orders, 86.5% on time) had met the 95% target: **2,251 fewer late orders**, overall on-time **93.2% → 95.6%**, about **1,200 fewer** 1-2 star reviews | Logistics Manager |
| 2 | **Seller handover rule**: maximum 3 days from payment approval to carrier pickup, tracked weekly on the seller scorecard | On-time %, Avg handover days | Capping handover at 3 days turns **1,278 late orders on time**: on-time **93.2% → 94.6%** (+1.3 points), about **680 fewer** negative reviews | Seller Success Manager |
| 3 | **Seller watch-list programme**: coaching then penalties for the 110 watch-list sellers | Late %, Negative review % | Bringing them to the platform's average late rate: **663 fewer late orders**, on-time **→ 93.9%**, about **350 fewer** negative reviews | Seller Success Manager |
| 4 | **Route-based delivery estimates (test, not a blanket cut)** | Conversion (future), On-time % | Promises are padded (17.6 days promised vs 7.9 actual same-state; 27.2 vs 15.1 inter-state), but cutting every estimate by 3 days would drop on-time to ~89%. Pilot route-specific estimates in a few low-risk same-state routes first | Logistics Manager + Product |

*Impacts are not additive (the same late orders can be fixed by more than one action). Recommendations 1 and 2 together are the priority.*

## Proposed targets for next year
* **On-time delivery ≥ 95%** every month, including peak months (currently 93.2% overall, 81-88% at peaks).
* **Average seller handover ≤ 2.5 days** (currently 2.85).
* **Negative review rate ≤ 12%** (currently 14.7%).

## Limits of the evidence
* Observational data: these are associations, not proven causes; recommendation 4 should be tested before rollout.
* Sizing assumes other factors stay the same; real impacts may be smaller.
* Data covers 2016-2018 only; distance and carrier identity are not in the dataset.

**Decision requested:** approve recommendations 1-3 for next year's logistics budget and seller policy, and a pilot for recommendation 4.

Evidence: SQL `04_sql/03_analysis.sql` (SQL-05, SQL-08, SQL-10, SQL-11, SQL-12, SQL-15), notebook `05_python/eda.ipynb` (sections 5-7, 10, and section 11 for every sized impact), Power BI pages Executive / Delivery / Seller scorecard.
