"""
eda.py - BazaarLink Day 4 EDA as a plain Python script (same code as eda.ipynb).

Run it in IDLE (open this file, press F5) or from a terminal inside 05_python:
    python eda.py
Tables and test results are printed. Each chart opens in a window (plt.show()):
close the chart window to continue to the next one. Charts are also saved to figures/.
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # so relative paths work from IDLE
import pandas as pd

def display(obj):
    """Print tables nicely (stands in for Jupyter's display)."""
    print(obj.to_string() if hasattr(obj, 'to_string') else obj)
    print()


# ============================================================================
# # BazaarLink: Delivery Performance and Customer Satisfaction EDA
#
# **Capstone Day 4: Python EDA and statistics**
#
# This notebook answers business questions Q1-Q11 from the BRD with descriptive statistics, charts and
# hypothesis tests. It uses the reusable module in `src/` (`loader.py`, `analysis.py`) and exports the headline
# KPIs to `kpi_summary.json`.
#
# **KPI rules (BRD section 7, identical to SQL `03_analysis.sql`):**
# * Revenue = sum of item price for delivered orders (freight excluded); AOV = Revenue / delivered orders
# * Delivery KPIs use delivered orders with a delivered date only
# * On time = delivered date on or before the estimated date; delay days = delivered minus estimated (positive = late)
# * Negative review = score 1 or 2; customers counted by `customer_unique_id`
# * Trends use complete months only: Jan 2017 to Aug 2018
#
# | Section | Business question |
# |---|---|
# | 1 | Q1 Orders and revenue trend, seasonality |
# | 2 | Q2 Revenue by category and state |
# | 3 | Q4-Q6 On-time trend, delivery by state, where time is lost |
# | 4 | Q7 Descriptive statistics: are estimated dates realistic? |
# | 5 | Q8 Hypothesis tests: do late orders get lower reviews? |
# | 6 | Q9 Conditional probability of a negative review |
# | 7 | Q10 Correlation and regression: what explains delivery time? |
# | 8 | Q11 Retention: do late first orders reduce repeat purchases? |
# | 9 | Change request CR-01: instalments, AOV and cancellations |
# | 10 | Findings and KPI export |
# ============================================================================
import os, sys, warnings
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from loader import CleanDataLoader, MissingColumnError
from analysis import OrdersAnalyser, ALPHA

DATA_DIR = os.path.join("..", "02_data", "cleaned")
FIG_DIR = "figures"
os.makedirs(FIG_DIR, exist_ok=True)

LATE, ON_TIME, NAVY, GREY = "#C0392B", "#1B998B", "#1F3A5F", "#8C96A3"
sns.set_theme(style="whitegrid", font_scale=0.95)
pd.set_option("display.max_columns", 30); pd.set_option("display.width", 160)

def save(fig, name):
    """Save a figure to figures/ for the deck and README."""
    fig.savefig(os.path.join(FIG_DIR, name), dpi=130, bbox_inches="tight")

print("Run at", datetime.now().strftime("%Y-%m-%d %H:%M"))

loader = CleanDataLoader(DATA_DIR)
try:
    orders = loader.load_orders_master()
except MissingColumnError as err:
    print("Data problem:", err)
    raise
finally:
    print(pd.DataFrame(loader.load_log))

a = OrdersAnalyser(orders)
print(f"{len(orders):,} orders x {orders.shape[1]} columns")

# Exception handling demo: a file without the required columns raises the custom MissingColumnError
try:
    loader.read_csv("customers.csv", required_columns=["customer_id", "column_that_does_not_exist"])
except MissingColumnError as err:
    print("Caught MissingColumnError ->", err)

kpis = a.kpis()
display(pd.Series(kpis, name="value").to_frame())


# ============================================================================
# These headline KPIs match SQL query **SQL-18** and the Excel quick-look exactly (Revenue R$ 13,221,498.11,
# on-time 93.23%, repeat customers 3.12%), which meets the "numbers match within 1%"
# success criterion.
# ============================================================================

# ============================================================================
# ## 1. Q1: How have orders and revenue trended? Is there seasonality or a peak event?
# ============================================================================
trend = a.monthly_trend()
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.bar(trend.index, trend["revenue"] / 1e3, color="#C9D6E3", label="Monthly revenue (R$ k)")
ax.plot(trend.index, trend["revenue_3m_avg"] / 1e3, color=NAVY, lw=2.5, label="3-month rolling average")
ax2 = ax.twinx(); ax2.plot(trend.index, trend["orders"], color="#E59500", marker="o", lw=1.5, label="Orders")
ax2.grid(False); ax.set_ylabel("Revenue (R$ thousands)"); ax2.set_ylabel("Orders")
ax.tick_params(axis="x", rotation=60)
peak = trend["orders"].idxmax()
ax.set_title(f"Orders grew through 2017 and peaked in {peak} (Black Friday); 2018 plateaued", loc="left", fontsize=12)
fig.legend(loc="lower right", bbox_to_anchor=(0.9, 0.22)); save(fig, "01_monthly_trend.png"); plt.show()
display(trend)

top_days = (orders.groupby(orders["order_purchase_timestamp"].dt.date)["order_id"].count()
                  .sort_values(ascending=False).head(5).rename("orders"))
weekday = (orders.groupby(orders["order_purchase_timestamp"].dt.day_name())["order_id"].count()
                 .reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))
display(top_days.to_frame()); display(weekday.to_frame("orders"))


# ============================================================================
# **Finding:** orders rose steadily through 2017, peaked in **2017-11** (7,544 orders) and plateaued
# at about 6,200-7,300 a month in 2018. The single biggest day is **24 Nov 2017 (Black Friday)**, more than double any
# other day: a promotional event, not normal seasonality. Weekdays (Mon-Tue) are busier than weekends.
# ============================================================================

# ============================================================================
# ## 2. Q2: Which categories and customer states bring the most revenue?
# ============================================================================
d = a.delivered()
cat = d.groupby("primary_category")["item_revenue"].sum().sort_values(ascending=False).head(10) / 1e3
state = d.groupby("customer_state")["item_revenue"].sum().sort_values(ascending=False)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
sns.barplot(x=cat.values, y=cat.index, color=NAVY, ax=axes[0])
axes[0].set_title("Health & beauty and watches lead category revenue", loc="left", fontsize=11)
axes[0].set_xlabel("Revenue (R$ thousands)"); axes[0].set_ylabel("")
share = (state / state.sum() * 100).head(10)
sns.barplot(x=share.values, y=share.index, color="#2E86AB", ax=axes[1])
axes[1].set_title(f"SP alone is {share.iloc[0]:.0f}% of revenue; top 3 states are {share.iloc[:3].sum():.0f}%", loc="left", fontsize=11)
axes[1].set_xlabel("Share of revenue (%)"); axes[1].set_ylabel("")
fig.tight_layout(); save(fig, "02_revenue_category_state.png"); plt.show()


# ============================================================================
# ## 3. Q4-Q6: Is on-time delivery improving? Where is it worst, and where is time lost?
# ============================================================================
fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(trend.index, trend["on_time_pct"], color=ON_TIME, marker="o", lw=2, label="On-time %")
ax.axhline(kpis["on_time_pct"], color=GREY, ls="--", lw=1, label=f"Overall {kpis['on_time_pct']}%")
ax2 = ax.twinx(); ax2.plot(trend.index, trend["avg_review"], color=LATE, marker="s", lw=1.5, label="Avg review score")
ax2.grid(False); ax.set_ylabel("On-time %"); ax2.set_ylabel("Average review score")
ax.tick_params(axis="x", rotation=60)
r = trend[["on_time_pct", "avg_review"]].corr().iloc[0, 1]
ax.set_title(f"On-time % dips at volume peaks (Nov-17, Feb-Mar-18) and review scores fall with it (r = {r:.2f})",
             loc="left", fontsize=12)
fig.legend(loc="lower left", bbox_to_anchor=(0.07, 0.15)); save(fig, "03_on_time_trend.png"); plt.show()

m = a.measurable()
top_states = m["customer_state"].value_counts().head(12).index
order_by = m[m["customer_state"].isin(top_states)].groupby("customer_state")["delivery_days"].median().sort_values().index
fig, ax = plt.subplots(figsize=(11, 4.2))
sns.boxplot(data=m[m["customer_state"].isin(top_states)], x="customer_state", y="delivery_days",
            order=order_by, showfliers=False, color="#C9D6E3", ax=ax)
ax.set_title("Customers far from the São Paulo seller base wait 2x longer (12 largest states, outliers hidden)",
             loc="left", fontsize=12)
ax.set_xlabel("Customer state"); ax.set_ylabel("Delivery days")
save(fig, "04_delivery_days_by_state_box.png"); plt.show()

by_state = a.stage_summary(by="customer_state").sort_values("delivery_days", ascending=False)
overall = a.stage_summary()
plot = pd.concat([overall.to_frame("ALL").T, by_state.head(8)])[["approval_days", "seller_handover_days", "carrier_days"]]
fig, ax = plt.subplots(figsize=(11, 4))
plot.plot(kind="barh", stacked=True, color=[GREY, "#E59500", NAVY], ax=ax)
ax.invert_yaxis(); ax.set_xlabel("Average days")
ax.set_title(f"The carrier leg is the biggest stage ({overall['carrier_days']} of {overall['delivery_days']} days); "
             f"seller handover adds {overall['seller_handover_days']}", loc="left", fontsize=12)
save(fig, "05_stage_breakdown.png"); plt.show()
display(by_state.head(8))


# ============================================================================
# **Finding (Q6):** on average an order spends **0.43 days** in payment approval,
# **2.85 days** with the seller before handover and **9.33 days** with the carrier.
# The carrier leg dominates, and it is longest for remote North/Northeast states (RR, AP, AM above 23 days).
# Seller handover is smaller but is the stage BazaarLink can control directly through seller policy.
# By region, the late rate is Northeast 12.7%, North 8.6%, Central-West 6.5%, Southeast 6.1%, South 5.9%.
# ============================================================================

# ============================================================================
# ## 4. Q7: Descriptive statistics. Are estimated delivery dates realistic?
# ============================================================================
desc_cols = ["delivery_days", "estimated_days", "delay_days", "approval_days", "seller_handover_days",
             "carrier_days", "review_score", "item_revenue", "freight_value"]
display(a.describe(desc_cols, m))

fig, ax = plt.subplots(figsize=(11, 4))
clip = m["delay_days"].clip(-60, 40)
ax.hist(clip[clip <= 0], bins=range(-60, 1), color=ON_TIME, label="On time / early")
ax.hist(clip[clip > 0], bins=range(1, 41), color=LATE, label="Late")
ax.axvline(0, color="black", lw=1)
early8 = (m["delay_days"] <= -8).mean() * 100
ax.set_title(f"{early8:.0f}% of orders arrive 8+ days before the promised date: estimates are heavily padded",
             loc="left", fontsize=12)
ax.set_xlabel("Delay days (delivered minus estimated; negative = early, clipped at -60 / +40)"); ax.set_ylabel("Orders")
ax.legend(); save(fig, "06_delay_histogram.png"); plt.show()
lo, hi = a.iqr_bounds(m["delivery_days"])
print(f"IQR fences for delivery days: {lo:.1f} to {hi:.1f}; outliers above: {(m['delivery_days'] > hi).sum():,} orders (kept, see DQ log)")


# ============================================================================
# **Finding (Q7):** shoppers are promised **23.7 days** on average but receive orders in
# **12.6 days**. The median order arrives **12 days early** and
# **74%** arrive 8 or more days early. The estimates are not realistic: they are padded so much that the on-time
# rate looks good, while the long promise itself may discourage purchases. Delivery days are right-skewed
# (skew 3.8): the mean is pulled up by a long tail of very slow deliveries, so medians are reported alongside means.
# ============================================================================

# ============================================================================
# ## 5. Q8: Do late orders get significantly lower review scores?
#
# **Test 1: Mann-Whitney U (main test)**
# * **H0:** review scores of late orders and on-time orders come from the same distribution.
# * **H1:** late orders have **lower** review scores (one-sided).
# * **alpha = 0.05**
# * **Why this test:** review score is an ordinal 1-5 scale and is heavily skewed (most scores are 5), so it is not normally
#   distributed. Mann-Whitney compares ranks and does not assume normality. A Welch t-test (unequal variances) is run as a
#   robustness check, which is valid here because the samples are large.
# ============================================================================
res = a.test_review_late_vs_on_time()
display(pd.Series(res).to_frame("value"))

r = a.reviewed_measurable()
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
sns.boxplot(data=r, x="delivery_status", y="review_score", order=["On time", "Late"],
            palette=[ON_TIME, LATE], ax=axes[0])
axes[0].set_title(f"Median review: {res['median_on_time']:.0f} on time vs {res['median_late']:.0f} late",
                  loc="left", fontsize=11)
axes[0].set_xlabel(""); axes[0].set_ylabel("Review score")
dist = pd.crosstab(r["delivery_status"], r["review_score"], normalize="index").loc[["On time", "Late"]] * 100
dist.T.plot(kind="bar", color=[ON_TIME, LATE], ax=axes[1])
axes[1].set_title("Late orders: most reviews are 1-star; on-time: most are 5-star", loc="left", fontsize=11)
axes[1].set_ylabel("% of reviews"); axes[1].set_xlabel("Review score"); axes[1].tick_params(axis="x", rotation=0)
fig.tight_layout(); save(fig, "07_review_late_vs_on_time.png"); plt.show()


# ============================================================================
# **Result:** the average review is **2.271** for late orders vs **4.29** for on-time orders.
# The Mann-Whitney p-value is below 0.001 (and the Welch t-test agrees, t = -100.74), so we **reject H0**.
#
# **In business words:** if late delivery made no difference to reviews, a gap this large would almost never happen by chance.
# Late delivery is strongly associated with worse reviews. The effect is large, not just significant (rank-biserial
# effect size 0.638): it is not a statistical technicality caused by the big sample.
#
# **Test 2: Chi-square test of independence (late vs negative review)**
# * **H0:** whether an order is late and whether its review is negative (1-2 stars) are independent.
# * **H1:** they are associated. alpha = 0.05.
# * **Why this test:** both variables are categorical (yes/no), and every expected cell count is far above 5.
# ============================================================================
chi = a.chi_square("is_late", "is_negative")
display(chi["table"].rename(index={0: "On time", 1: "Late"}, columns={0: "Not negative", 1: "Negative"}))
print({k: v for k, v in chi.items() if k != "table"})


# ============================================================================
# **Result:** chi-square = 15,054.6, p < 0.001: **reject H0**. Late delivery and
# negative reviews are not independent; Cramér's V = 0.396 shows a moderate-to-strong
# association. Note this shows association, not proof that lateness alone causes the bad review (some late orders also
# had damaged or wrong items).
# ============================================================================

# ============================================================================
# ## 6. Q9: What is the probability of a negative review given a late delivery vs an on-time one?
# ============================================================================
p = a.negative_review_probability()
print(f"P(negative | late)    = {p['p_negative_given_late']:.3f}")
print(f"P(negative | on time) = {p['p_negative_given_on_time']:.3f}")
print(f"Relative risk         = {p['relative_risk']}x")
bucket = p["by_bucket"]
fig, ax = plt.subplots(figsize=(9, 3.8))
sns.barplot(x=bucket.index, y=bucket["p_negative"] * 100, palette=[ON_TIME, "#F0B37E", "#E07A5F", LATE], ax=ax)
for i, v in enumerate(bucket["p_negative"] * 100):
    ax.text(i, v + 1.5, f"{v:.0f}%", ha="center")
ax.set_ylim(0, 95); ax.set_ylabel("P(negative review) %"); ax.set_xlabel("")
ax.set_title("Even 1-3 days late triples the chance of a 1-2 star review; 8+ days late: 4 in 5 are negative",
             loc="left", fontsize=12)
save(fig, "08_negative_review_by_delay_bucket.png"); plt.show()
display(bucket)


# ============================================================================
# **Finding (Q9):** P(negative | late) = **62.4%** vs P(negative | on time) =
# **9.3%**: a late order is **6.73x** as likely to get a 1-2 star review.
# The risk climbs with every bucket: 32% at 1-3 days late, 68% at 4-7 days and
# 79% at 8+ days. This answers the Head of CX: there is no "safe" amount of lateness.
# ============================================================================

# ============================================================================
# ## 7. Q10: Which factors explain delivery time?
#
# Candidate drivers: product weight, freight value, inter-state shipping (seller and customer in different states),
# and seller handover days. First a correlation matrix, then ordinary least-squares regression (NumPy).
# ============================================================================
corr_cols = ["delivery_days", "weight_kg", "freight_value", "inter_state", "seller_handover_days",
             "estimated_days", "item_revenue", "review_score"]
corr = m[corr_cols].corr()
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, ax=ax)
ax.set_title("Delivery days move most with handover time and inter-state routes; weight barely matters",
             loc="left", fontsize=11)
save(fig, "09_correlation_heatmap.png"); plt.show()

reg1 = a.regression(x=("weight_kg", "freight_value", "inter_state"))
print(f"Model 1 (brief's factors): n = {reg1['n']:,}, R² = {reg1['r_squared']}")
display(reg1["coefficients"])
reg2 = a.regression(x=("weight_kg", "freight_value", "inter_state", "seller_handover_days"))
print(f"Model 2 (+ seller handover days): R² = {reg2['r_squared']}")
display(reg2["coefficients"])

sample = m[["seller_handover_days", "delivery_days"]].dropna()
sample = sample[(sample["seller_handover_days"] <= 15) & (sample["delivery_days"] <= 60)].sample(5000, random_state=42)
fig, ax = plt.subplots(figsize=(9, 4.5))
sns.regplot(data=sample, x="seller_handover_days", y="delivery_days", scatter_kws={"alpha": 0.15, "s": 10, "color": NAVY},
            line_kws={"color": LATE, "lw": 2}, ax=ax)
ax.set_title("Every extra day a seller holds an order adds about a day to delivery (sample of 5,000 orders)",
             loc="left", fontsize=12)
ax.set_xlabel("Seller handover days"); ax.set_ylabel("Delivery days")
save(fig, "10_handover_vs_delivery_scatter.png"); plt.show()


# ============================================================================
# **Interpretation:**
# * **Model 1** (weight, freight, inter-state) explains **14%** of the variation in delivery days (R² = 0.1379).
#   Holding the others constant, an **inter-state** order takes **6.9 days longer** than a
#   same-state order. Each extra kg adds only 0.07 days and each extra R$ 1 of freight
#   0.024 days: statistically significant (huge sample) but practically small.
# * **Model 2** adds seller handover days and R² doubles to **28%**. Each extra handover day adds
#   **1.05 delivery days**, almost one-for-one.
#
# **Limits (state these when presenting):**
# * R² of 0.28 means most variation is unexplained: distance, carrier, region and season are missing.
# * This is association, not causation: heavier items are also more often inter-state, so effects overlap
#   (weight even changes sign once handover is added).
# * Delivery days are right-skewed, so residuals are not normal; coefficients are fine for direction and size, but
#   p-values should be read with care.
# ============================================================================

# ============================================================================
# ## 8. Q11: Do customers whose first order was late return less often?
#
# * **H0:** whether a customer's first order was late is independent of whether they ever order again.
# * **H1:** they are associated. Chi-square test, alpha = 0.05.
# ============================================================================
first, ret = a.retention_by_first_order()
print(f"Repeat customer rate overall: {kpis['repeat_customer_pct']}% of {kpis['customers']:,} customers "
      f"(counted by customer_unique_id; by customer_id it would look like 0%)")
display(ret)
chi_r = a.chi_square("first_order", "returned", first)
print({k: v for k, v in chi_r.items() if k != "table"})
fig, ax = plt.subplots(figsize=(6.5, 3.6))
sns.barplot(x=ret.index, y=ret["repeat_rate"] * 100, palette=[LATE, ON_TIME], ax=ax)
for i, v in enumerate(ret["repeat_rate"] * 100):
    ax.text(i, v + 0.08, f"{v:.2f}%", ha="center")
ax.set_ylabel("Customers who ordered again (%)"); ax.set_xlabel("First order was...")
ax.set_title("Customers with a late first order come back less often", loc="left", fontsize=11)
save(fig, "11_retention_first_order.png"); plt.show()


# ============================================================================
# **Finding (Q11):** only **3.12%** of 96,096 customers ever order twice. Customers whose
# first order was late return at **2.54%** vs **3.13%**
# when it was on time: about 19% fewer returners.
# The chi-square p-value is 0.010 (< 0.05), so the difference is statistically significant, but the
# effect is small (Cramér's V = 0.008). Late delivery hurts retention, but low repeat purchase is a
# wider problem than delivery alone.
# ============================================================================

# ============================================================================
# ## 9. Change request CR-01 (Finance): instalments, AOV and cancellations
#
# **Request (Day 4):** "Do orders paid in more instalments have a higher AOV or more cancellations?"
# Logged as CR-01 in the change log; impact: one extra analysis section, one Excel chart (already in the quick-look) and
# one SQL query (SQL-04b). No change to KPI definitions. Sponsor approval recorded in the Confluence decision log.
# ============================================================================
inst, rho = a.instalment_analysis()
display(inst); print("Spearman correlation, instalments vs order value:", rho)
fig, ax = plt.subplots(figsize=(8, 3.8))
sns.barplot(x=inst.index.astype(str), y=inst["aov_brl"], color=NAVY, ax=ax)
ax2 = ax.twinx(); ax2.plot(range(len(inst)), inst["cancellation_pct"], color=LATE, marker="o", lw=2)
ax2.set_ylim(0, 3); ax2.set_ylabel("Cancellation %", color=LATE); ax2.grid(False)
ax.set_ylabel("AOV (R$)"); ax.set_xlabel("Number of instalments")
ax.set_title("AOV triples with 7+ instalments; cancellations stay flat (~1.1-1.4%)", loc="left", fontsize=11)
save(fig, "12_instalments_aov_cancellation.png"); plt.show()


# ============================================================================
# **Finding (CR-01):** AOV rises from **R$ 100** (single payment) to
# **R$ 301** (7+ instalments); Spearman rho = 0.375 (p < 0.001). Cancellation rates
# stay between 1.07% and 1.35% with no upward trend. Instalments
# enable bigger baskets without more cancellations. Caveat: causation probably runs the other way (expensive items are
# paid in instalments), so this supports keeping interest-free instalments, not forcing them.
# ============================================================================

# ============================================================================
# ## 10. Key findings
#
# 1. **Late delivery is strongly associated with bad reviews.** Late orders average 2.271 stars vs 4.29
#    (Mann-Whitney p < 0.001, large effect). A late order is 6.73x as likely to get a 1-2 star review.
# 2. **There is no safe lateness.** P(negative) rises from 9% on time to 32% at 1-3 days,
#    68% at 4-7 days and 79% at 8+ days late.
# 3. **On-time % is high overall (93.23%) but collapses at volume peaks:** 2018-03 fell to
#    81.0%, and monthly review scores track on-time % closely.
# 4. **Estimated dates are heavily padded:** promised 23.7 days vs actual 12.6;
#    74% arrive 8+ days early. There is room to promise faster dates without hurting on-time %.
# 5. **Inter-state shipping is the biggest structural delay:** +6.9 days vs same-state orders
#    (same-state average 7.9 days vs inter-state 15.1).
# 6. **Seller handover is the controllable lever:** each extra handover day adds ~1.0
#    delivery day. A what-if cap of 3 handover days would lift on-time from 93.23% to 94.6%
#    (+1.3 points).
# 7. **The carrier leg is the largest stage** (9.33 of 12.56 days), longest for remote
#    North/Northeast states.
# 8. **Retention is very low (3.12%)** and lower still after a late first order
#    (2.54% vs 3.13%, significant but small effect).
# 9. **Black Friday (2017-11) is the single biggest event**: plan carrier and seller capacity ahead of it.
# 10. **CR-01:** more instalments mean higher AOV (R$ 301 at 7+) with no rise in cancellations.
#
# **Limits:** observational data (association, not causation); 2016 and Sep-Oct 2018 excluded from trends; regression
# explains 28% of delivery time; review text not analysed.
# ============================================================================

# ============================================================================
# ## 11. Recommendation sizing (what-if scenarios)
#
# Each recommendation in the memo is sized here, so every number traces to this cell. Method: change one driver, keep
# everything else the same, recount late orders. Negative reviews avoided = late orders fixed ×
# (P(negative | late) − P(negative | on time)). These are estimates from observational data, not guarantees, and the
# scenarios overlap, so they are not additive.
# ============================================================================
# --- sizing ---
d = a.measurable().copy()
p = a.negative_review_probability()
gap = p["p_negative_given_late"] - p["p_negative_given_on_time"]
base_late = d["is_late"].sum()
rows = []

# R1: peak months held at the 95% target
d["month"] = d["order_purchase_timestamp"].dt.to_period("M").astype(str)
peak = d[d["month"].isin(["2017-11", "2017-12", "2018-02", "2018-03"])]
fixed = int(peak["is_late"].sum() - len(peak) * 0.05)
rows.append(("R1 Peak months at 95% on time", fixed, 1 - (base_late - fixed) / len(d)))

# R2: seller handover capped at 3 days
h = d["seller_handover_days"].fillna(0)
new_delay = np.ceil(d["delay_days"] - np.maximum(0, h - 3))
fixed = int(((d["is_late"] == 1) & (new_delay <= 0)).sum())
rows.append(("R2 Handover capped at 3 days", fixed, (new_delay <= 0).mean()))

# R3: watch-list sellers brought to the average late rate of all other sellers
items = loader.load("order_items.csv")
sc = pd.read_csv(os.path.join("..", "06_dashboards", "data", "vw_seller_scorecard.csv"))
watch = set(sc.loc[sc["watch_status"] == "Watch list", "seller_id"])
w_orders = set(items.loc[items["seller_id"].isin(watch), "order_id"])
dw = d[d["order_id"].isin(w_orders)]
rest_rate = d.loc[~d["order_id"].isin(w_orders), "is_late"].mean()
fixed = int(dw["is_late"].sum() - len(dw) * rest_rate)
rows.append((f"R3 {len(watch)} watch-list sellers at average late rate", fixed, 1 - (base_late - fixed) / len(d)))

sizing = pd.DataFrame(rows, columns=["scenario", "late_orders_fixed", "new_on_time"])
sizing["on_time_lift_pts"] = (sizing["new_on_time"] - (1 - base_late / len(d))) * 100
sizing["negative_reviews_avoided"] = (sizing["late_orders_fixed"] * gap).round()
sizing["new_on_time"] = (sizing["new_on_time"] * 100).round(2)
display(sizing.round(2))
print(f"Peak months: {len(peak):,} orders, on-time {100 * (1 - peak['is_late'].mean()):.1f}%")
print(f"Watch-list orders: {len(dw):,} ({100 * len(dw) / len(d):.1f}% of volume), late {100 * dw['is_late'].mean():.1f}% vs {100 * rest_rate:.1f}% for the rest")

# R4 check: a blanket cut of the estimate by N days (why we recommend a pilot, not a blanket cut)
cut = pd.DataFrame({"days_cut": [3, 5, 7],
                    "on_time_%": [round(100 * ((d["delay_days"] + n) <= 0).mean(), 1) for n in (3, 5, 7)]})
display(cut)
for ss, label in [(1, "Same state"), (0, "Inter-state")]:
    x = d[d["same_state"] == ss]
    print(f"{label}: promised {x['estimated_days'].mean():.1f} days, actual {x['delivery_days'].mean():.1f}, "
          f"on-time {100 * (1 - x['is_late'].mean()):.1f}%, on-time if cut by 3 days {100 * ((x['delay_days'] + 3) <= 0).mean():.1f}%")


extra = {
    "q8_mann_whitney": a.test_review_late_vs_on_time(),
    "q8_chi_square_late_vs_negative": {k: v for k, v in a.chi_square("is_late", "is_negative").items() if k != "table"},
    "q9_conditional_probability": {k: v for k, v in a.negative_review_probability().items() if k != "by_bucket"},
    "q10_regression_r_squared": {"model_1": reg1["r_squared"], "model_2_with_handover": reg2["r_squared"]},
    "q10_regression_coefficients_model_2": reg2["coefficients"]["coefficient"].round(3).to_dict(),
    "q11_repeat_rate_by_first_order": ret["repeat_rate"].to_dict(),
    "cr01_instalments": inst.reset_index().astype({"instalment_band": str}).to_dict(orient="records"),
}
path = a.export_kpis("kpi_summary.json", extra)
print("Saved", os.path.abspath(path))

print("\nDone. Charts saved in", os.path.abspath("figures"))
