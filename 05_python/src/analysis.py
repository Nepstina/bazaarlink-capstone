"""
analysis.py - reusable analysis for the BazaarLink capstone.

Classes
-------
BaseAnalyser    holds a DataFrame privately; descriptive statistics helpers
OrdersAnalyser  BazaarLink KPIs, delivery, satisfaction, retention and
                statistics methods (inherits BaseAnalyser)

All KPI definitions follow BRD section 7 and match 04_sql/03_analysis.sql
(SQL-18), so Python and SQL headline numbers agree.
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

from loader import MissingColumnError

ALPHA = 0.05


class BaseAnalyser:
    """Wraps a DataFrame (kept private) with generic descriptive helpers."""

    def __init__(self, df):
        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("BaseAnalyser needs a non-empty DataFrame")
        self._df = df

    @property
    def data(self):
        """A copy of the data, so callers cannot change the analyser's state."""
        return self._df.copy()

    def require(self, *columns):
        """Raise MissingColumnError if any column is absent."""
        missing = set(columns) - set(self._df.columns)
        if missing:
            raise MissingColumnError("analysis DataFrame", missing)

    def describe(self, columns, df=None):
        """Descriptive statistics table: count, mean, median, std, min, quartiles, max, skew."""
        d = (self._df if df is None else df)[list(columns)]
        out = d.describe().T
        out.insert(2, "median", d.median())
        out["skew"] = d.skew()
        return out.round(2)

    @staticmethod
    def iqr_bounds(series):
        """Lower and upper IQR fences (Q1 - 1.5*IQR, Q3 + 1.5*IQR)."""
        q1, q3 = series.quantile([0.25, 0.75])
        return q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)


class OrdersAnalyser(BaseAnalyser):
    """Analysis of the order-level master table (one row per order)."""

    TREND_START, TREND_END = "2017-01", "2018-08"

    def __init__(self, orders_master):
        super().__init__(orders_master)
        self.require("order_id", "order_status", "is_delivery_measurable", "is_late", "item_revenue")
        self._df = self._df.assign(
            purchase_month=self._df["order_purchase_timestamp"].dt.to_period("M").astype(str),
            weekday=self._df["order_purchase_timestamp"].dt.day_name(),
            weight_kg=self._df["total_weight_g"] / 1000,
            inter_state=1 - self._df["same_state"],
        )

    # ------------------------------------------------------------ subsets
    def delivered(self):
        """Orders with status 'delivered' (used for Revenue and AOV)."""
        return self._df[self._df["order_status"] == "delivered"]

    def measurable(self):
        """Delivered orders with a delivered date (used for all delivery KPIs)."""
        return self._df[self._df["is_delivery_measurable"] == 1]

    def reviewed_measurable(self):
        """Measurable orders that have a review score."""
        m = self.measurable()
        return m[m["review_score"].notna()]

    # ------------------------------------------------------------ KPIs
    def kpis(self):
        """Headline KPIs exactly as defined in the BRD (same as SQL-18)."""
        df, d, m = self._df, self.delivered(), self.measurable()
        revenue = d["item_revenue"].sum()
        per_customer = df.groupby("customer_unique_id")["order_id"].nunique()
        return {
            "orders": int(df["order_id"].nunique()),
            "delivered_orders": int(len(d)),
            "revenue_brl": round(float(revenue), 2),
            "aov_brl": round(float(revenue / len(d)), 2),
            "freight_brl": round(float(d["freight_value"].sum()), 2),
            "freight_ratio_pct": round(float(100 * d["freight_value"].sum() / revenue), 2),
            "on_time_pct": round(float(100 * (1 - m["is_late"].mean())), 2),
            "avg_delivery_days": round(float(m["delivery_days"].mean()), 2),
            "avg_delay_days": round(float(m["delay_days"].mean()), 2),
            "avg_seller_handover_days": round(float(m["seller_handover_days"].mean()), 2),
            "avg_review_score": round(float(df["review_score"].mean()), 3),
            "negative_review_pct": round(float(100 * df["is_negative"].mean()), 2),
            "customers": int(len(per_customer)),
            "repeat_customer_pct": round(float(100 * (per_customer >= 2).mean()), 2),
            "cancellation_pct": round(float(100 * df["is_cancelled"].mean()), 2),
        }

    # ------------------------------------------------------------ Q1 trend
    def monthly_trend(self):
        """Monthly orders, revenue, on-time % and 3-month rolling revenue (complete months only)."""
        df = self._df[(self._df["purchase_month"] >= self.TREND_START) & (self._df["purchase_month"] <= self.TREND_END)]
        g = df.groupby("purchase_month").agg(
            orders=("order_id", "count"),
            revenue=("item_revenue", lambda s: s[df.loc[s.index, "order_status"] == "delivered"].sum()),
            on_time_pct=("is_late", lambda s: 100 * (1 - s.mean())),
            avg_review=("review_score", "mean"),
        )
        g["revenue_3m_avg"] = g["revenue"].rolling(3, min_periods=1).mean()
        return g.round(2)

    # ------------------------------------------------------------ Q6 stages
    def stage_summary(self, by=None):
        """Average days per journey stage (approval, seller handover, carrier)."""
        cols = ["approval_days", "seller_handover_days", "carrier_days", "delivery_days"]
        m = self.measurable()
        if by is None:
            return m[cols].mean().round(2)
        return m.groupby(by)[cols].mean().round(2).assign(orders=m.groupby(by).size())

    # ------------------------------------------------------------ Q8 tests
    def test_review_late_vs_on_time(self):
        """Mann-Whitney U (main test) and Welch t-test (check) on review score, late vs on time.

        H0: late and on-time orders have the same review score distribution.
        H1: late orders have LOWER review scores (one-sided).
        """
        r = self.reviewed_measurable()
        late = r.loc[r["is_late"] == 1, "review_score"]
        on_time = r.loc[r["is_late"] == 0, "review_score"]
        mw = stats.mannwhitneyu(late, on_time, alternative="less")
        tt = stats.ttest_ind(late, on_time, equal_var=False, alternative="less")
        rank_biserial = 1 - 2 * mw.statistic / (len(late) * len(on_time))
        return {
            "n_late": int(len(late)), "n_on_time": int(len(on_time)),
            "mean_late": round(float(late.mean()), 3), "mean_on_time": round(float(on_time.mean()), 3),
            "median_late": float(late.median()), "median_on_time": float(on_time.median()),
            "mann_whitney_U": float(mw.statistic), "mann_whitney_p": float(mw.pvalue),
            "welch_t": round(float(tt.statistic), 2), "welch_p": float(tt.pvalue),
            "effect_size_rank_biserial": round(float(abs(rank_biserial)), 3),
            "reject_H0": bool(mw.pvalue < ALPHA),
        }

    def chi_square(self, row, col, df=None):
        """Chi-square test of independence between two categorical columns."""
        d = self.reviewed_measurable() if df is None else df
        table = pd.crosstab(d[row], d[col])
        chi2, p, dof, expected = stats.chi2_contingency(table)
        n = table.values.sum()
        cramers_v = np.sqrt(chi2 / (n * (min(table.shape) - 1)))
        return {"table": table, "chi2": round(float(chi2), 1), "p_value": float(p), "dof": int(dof),
                "cramers_v": round(float(cramers_v), 3), "reject_H0": bool(p < ALPHA),
                "min_expected": round(float(expected.min()), 1)}

    # ------------------------------------------------------------ Q9 probability
    def negative_review_probability(self):
        """P(negative review | delivery status) and | delay bucket, with relative risk."""
        r = self.reviewed_measurable()
        p_late = r.loc[r["is_late"] == 1, "is_negative"].mean()
        p_on_time = r.loc[r["is_late"] == 0, "is_negative"].mean()
        by_bucket = (r.groupby("delay_bucket")["is_negative"].agg(["count", "mean"])
                      .rename(columns={"count": "reviewed_orders", "mean": "p_negative"})
                      .reindex(["On time", "1-3 days late", "4-7 days late", "8+ days late"]))
        return {"p_negative_given_late": round(float(p_late), 4),
                "p_negative_given_on_time": round(float(p_on_time), 4),
                "relative_risk": round(float(p_late / p_on_time), 2),
                "p_negative_overall": round(float(r["is_negative"].mean()), 4),
                "by_bucket": by_bucket.round(4)}

    # ------------------------------------------------------------ Q10 regression
    def regression(self, y="delivery_days", x=("weight_kg", "freight_value", "inter_state")):
        """Ordinary least squares with NumPy: coefficients, standard errors, p-values and R-squared."""
        d = self.measurable()[[y, *x]].dropna()
        X = np.column_stack([np.ones(len(d)), d[list(x)].to_numpy(dtype=float)])
        Y = d[y].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        resid = Y - X @ beta
        n, k = X.shape
        sigma2 = resid @ resid / (n - k)
        se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
        t = beta / se
        p = 2 * stats.t.sf(np.abs(t), n - k)
        r2 = 1 - (resid @ resid) / ((Y - Y.mean()) @ (Y - Y.mean()))
        coef = pd.DataFrame({"coefficient": beta, "std_error": se, "t": t, "p_value": p},
                            index=["intercept", *x]).round(4)
        return {"n": int(n), "r_squared": round(float(r2), 4),
                "adj_r_squared": round(float(1 - (1 - r2) * (n - 1) / (n - k)), 4), "coefficients": coef}

    # ------------------------------------------------------------ Q11 retention
    def retention_by_first_order(self):
        """Repeat rate for customers whose first order was late vs on time."""
        df = self._df.sort_values("order_purchase_timestamp")
        first = df.groupby("customer_unique_id").head(1).copy()
        first["returned"] = (first["customer_total_orders"] >= 2).astype(int)
        first = first[first["is_delivery_measurable"] == 1]
        first["first_order"] = np.where(first["is_late"] == 1, "Late", "On time")
        summary = first.groupby("first_order")["returned"].agg(customers="count", repeat_rate="mean")
        return first, summary.round(4)

    # ------------------------------------------------------------ CR-01 instalments
    def instalment_analysis(self):
        """Change request CR-01: AOV and cancellation rate by number of instalments."""
        df = self._df[self._df["max_installments"].notna()].copy()
        df["instalment_band"] = pd.cut(df["max_installments"], [0, 1, 3, 6, 24],
                                       labels=["1 (single)", "2-3", "4-6", "7+"])
        d = df[df["order_status"] == "delivered"]
        out = pd.DataFrame({
            "orders": df.groupby("instalment_band", observed=True).size(),
            "aov_brl": d.groupby("instalment_band", observed=True)["item_revenue"].mean(),
            "cancellation_pct": 100 * df.groupby("instalment_band", observed=True)["is_cancelled"].mean(),
        }).round(2)
        rho, p = stats.spearmanr(d["max_installments"], d["item_revenue"])
        return out, {"spearman_rho": round(float(rho), 3), "p_value": float(p)}

    # ------------------------------------------------------------ export
    def export_kpis(self, path, extra=None):
        """Write the headline KPIs (plus optional extra results) to a JSON file."""
        payload = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "source": "02_data/cleaned/orders_master.csv",
                   "definitions": "BRD v1 section 7; matches SQL-18 in 04_sql/03_analysis.sql",
                   "kpis": self.kpis()}
        if extra:
            payload["results"] = extra
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        return path
