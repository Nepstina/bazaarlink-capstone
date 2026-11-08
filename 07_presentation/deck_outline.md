# Final deck outline (Gamma): 12 slides, 10 minutes

Paste this outline into Gamma (Create → Paste in text), then replace placeholder images with the screenshots and
charts named on each slide. Every number below comes from SQL-18 / the notebook; check each one after Gamma builds it.
Speaker time in brackets.

---

### 1. Delivering on the Promise (0:20)
BazaarLink delivery performance and customer satisfaction · [your name] · [date]
Image: Power BI Executive page screenshot.

### 2. The problem (0:45)
* Growth has stalled: bad delivery → bad reviews → customers don't return
* Each team had its own numbers; nobody agreed on the on-time rate
* Question: what is late delivery costing us, and where do we act first?

### 3. Data and approach (0:45)
* 99,441 orders, 9 linked tables, 2016-2018 (Olist)
* Cleaned in Python (48 data issues logged) → MySQL (25 queries, 3 views) → Python statistics → Power BI, Tableau, Excel
* One KPI definition set: all tools match exactly
Image: Power BI model view (star schema).

### 4. Headline numbers (0:45)
On-time **93.2%** · Avg delivery **12.6 days** · Avg review **4.09** · Negative reviews **14.7%** · Repeat customers **3.1%** · Revenue **R$ 13.2M**

### 5. Late delivery is strongly linked to bad reviews (1:00)
* Late orders: **2.27 stars** vs **4.29** on time (Mann-Whitney p < 0.001)
* A late order is **6.7×** as likely to get a 1-2 star review
Image: `05_python/figures/07_review_late_vs_on_time.png`

### 6. There is no safe lateness (0:45)
* P(negative review): **9%** on time → **32%** 1-3 days late → 68% → **79%** 8+ days late
Image: `figures/08_negative_review_by_delay_bucket.png`

### 7. When: on-time collapses at peaks (0:45)
* 93.2% overall, but **87.6%** Nov-17 (Black Friday), **85.9%** Feb-18, **81.0%** Mar-18
Image: `figures/03_on_time_trend.png` or Power BI on-time chart with the 95% target

### 8. Where time is lost (1:00)
* Carrier leg **9.3** of 12.6 days; seller handover **2.9**; approval 0.4
* Inter-state **15.1 vs 7.9 days** same-state (+6.9 days in the regression)
* Each extra handover day ≈ +1 delivery day
Image: `figures/05_stage_breakdown.png` + Tableau map

### 9. Who: a concentrated group of sellers (0:45)
* **110 sellers** (30+ orders) on the watch list: late ≥ 12% or review < 3.8
* Their orders are late **12.2%** vs **6.1%** for everyone else
Image: Power BI Seller scorecard

### 10. Recommendations, sized (1:30)
| Action | KPI | Impact |
|---|---|---|
| Peak-season capacity plan | On-time % | 93.2% → **95.6%**, ~1,200 fewer bad reviews |
| Seller handover ≤ 3 days | On-time % | → **94.6%**, ~680 fewer bad reviews |
| Watch-list programme (110 sellers) | Late %, negative reviews | → **93.9%**, ~350 fewer bad reviews |
| Route-based estimates: pilot only | Conversion | blanket 3-day cut would drop on-time to 88.8% |
Proposed target: **on-time ≥ 95% every month**.

### 11. Dashboard demo (1:30)
Live: Power BI Executive → Delivery (region slicer) → Seller scorecard → right-click drill-through → Tableau map click filter.

### 12. Next steps and limits (0:30)
* Approve actions 1-3; pilot action 4; roll out KPIs (change management plan)
* Limits: associations, not proven causes; no distance or carrier data; regression R² 0.28
* Questions?

---

## Likely Q&A (practise these)
* **Why Mann-Whitney?** Review scores are ordinal (1-5) and skewed; Mann-Whitney compares ranks without assuming normality; a Welch t-test agrees.
* **What does p < 0.001 mean?** If lateness made no difference, a gap this large would almost never happen by chance.
* **Is lateness the cause of bad reviews?** Strong association; some late orders also had other problems, so we say "linked", not "caused".
* **Why customer_unique_id?** customer_id changes every order; using it would show ~0% repeat customers.
* **Why do payment totals not match revenue?** Payments include freight and instalment interest; revenue = item price of delivered orders only.
* **How did you check the dashboards?** A KPI Check page in Power BI and a check in Tableau, both matching SQL-18 exactly.
* **Why are North states rarely late even though delivery takes longest?** Their promised dates are longer; the late-rate problem is the Northeast.
* **Are the impacts additive?** No: the scenarios overlap; actions 1 and 2 are the priority.
