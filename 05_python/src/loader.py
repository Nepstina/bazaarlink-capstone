"""
loader.py - reusable data loading for the BazaarLink capstone.

Classes
-------
MissingColumnError  custom exception raised when a CSV lacks a required column
BaseLoader          generic CSV loader: path handling, validation, load log
CleanDataLoader     loads the cleaned BazaarLink tables (inherits BaseLoader)
"""

import os
from datetime import datetime

import pandas as pd


class MissingColumnError(Exception):
    """Raised when a loaded file does not contain every required column."""

    def __init__(self, file_name, missing):
        self.file_name = file_name
        self.missing = sorted(missing)
        super().__init__(f"{file_name} is missing required column(s): {', '.join(self.missing)}")


class BaseLoader:
    """Generic CSV loader.

    Keeps the data folder private (encapsulation) and records every load
    attempt in a log so data problems can be traced.
    """

    def __init__(self, data_dir):
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Data folder not found: {data_dir}")
        self._data_dir = data_dir
        self._log = []

    @property
    def data_dir(self):
        """Folder the loader reads from (read-only)."""
        return self._data_dir

    @property
    def load_log(self):
        """List of dicts describing each load attempt (file, rows, status, time)."""
        return list(self._log)

    def read_csv(self, file_name, required_columns=(), parse_dates=()):
        """Read one CSV and check it has the required columns.

        Parameters
        ----------
        file_name : str            file inside the data folder, e.g. 'orders.csv'
        required_columns : iterable columns that must exist
        parse_dates : iterable      columns converted to datetime

        Returns
        -------
        pandas.DataFrame

        Raises
        ------
        FileNotFoundError, MissingColumnError
        """
        path = os.path.join(self._data_dir, file_name)
        started = datetime.now()
        status, rows = "failed", 0
        try:
            df = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
            missing = set(required_columns) - set(df.columns)
            if missing:
                raise MissingColumnError(file_name, missing)
            for col in parse_dates:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            rows = len(df)
            status = "ok"
            return df
        except FileNotFoundError:
            status = "file not found"
            raise
        except MissingColumnError as err:
            status = str(err)
            raise
        finally:
            self._log.append({
                "file": file_name,
                "rows": rows,
                "status": status,
                "seconds": round((datetime.now() - started).total_seconds(), 2),
                "loaded_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            })


class CleanDataLoader(BaseLoader):
    """Loads the cleaned BazaarLink tables written by clean_data.py."""

    REQUIRED = {
        "orders_master.csv": [
            "order_id", "customer_unique_id", "customer_state", "order_status",
            "order_purchase_timestamp", "order_estimated_delivery_date",
            "is_delivered", "is_delivery_measurable", "is_late", "delivery_days", "delay_days",
            "approval_days", "seller_handover_days", "carrier_days", "estimated_days",
            "item_revenue", "freight_value", "total_weight_g", "same_state",
            "review_score", "is_negative", "max_installments", "main_payment_type",
            "primary_category", "primary_seller_state", "delay_bucket", "is_cancelled",
        ],
        "order_items.csv": ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"],
        "reviews.csv": ["order_id", "review_score"],
    }
    DATES = {
        "orders_master.csv": ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
                              "order_delivered_customer_date", "order_estimated_delivery_date"],
    }

    def load(self, file_name):
        """Load a cleaned table with its required columns and date columns."""
        return self.read_csv(file_name, self.REQUIRED.get(file_name, ()), self.DATES.get(file_name, ()))

    def load_orders_master(self):
        """One row per order with customer, item, payment and review data."""
        return self.load("orders_master.csv")
