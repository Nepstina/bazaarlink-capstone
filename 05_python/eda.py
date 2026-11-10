
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))  
import pandas as pd

def display(obj):
    """Print tables nicely (stands in for Jupyter's display)."""
    print(obj.to_string() if hasattr(obj, 'to_string') else obj)
    print()


# ============================================================================
# # BazaarLink: Delivery Performance and Customer Satisfaction EDA
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

try:
    loader.read_csv("customers.csv", required_columns=["customer_id", "column_that_does_not_exist"])
except MissingColumnError as err:
    print("Caught MissingColumnError ->", err)

kpis = a.kpis()
display(pd.Series(kpis, name="value").to_frame())


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
# ## 5. Q8: Do late orders get significantly lower review scores?
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


chi = a.chi_square("is_late", "is_negative")
display(chi["table"].rename(index={0: "On time", 1: "Late"}, columns={0: "Not negative", 1: "Negative"}))
print({k: v for k, v in chi.items() if k != "table"})



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
# ## 7. Q10: Which factors explain delivery time?
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
# ## 8. Q11: Do customers whose first order was late return less often?
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
# ## 9. Change request CR-01 (Finance): instalments, AOV and cancellations
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
# ## 11. Recommendation sizing (what-if scenarios)
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

# R4 check: a blanket cut of the estimate by N days 
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
