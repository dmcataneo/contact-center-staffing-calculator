"""Reading and validating the demand CSV."""

from __future__ import annotations

import math

import pandas as pd

REQUIRED_COLUMNS = {"period", "contacts"}


def validate_demand(df: pd.DataFrame) -> pd.DataFrame:
    """Check the demand CSV and return a ready-to-use DataFrame.

    Rules: 'period' and 'contacts' columns are required; at least one
    row; contacts numeric, finite and >= 0; no repeated periods.
    Raises ValueError with a clear message when something is off.
    """
    df = df.rename(columns={c: str(c).strip().lower() for c in df.columns})
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            "The CSV must have the columns 'period' and 'contacts'. "
            f"Missing: {', '.join(sorted(missing))}."
        )
    df = df[["period", "contacts"]].copy()
    if df.empty:
        raise ValueError("The CSV has no data rows.")
    try:
        df["contacts"] = pd.to_numeric(df["contacts"], errors="raise")
    except (ValueError, TypeError):
        raise ValueError("The 'contacts' column must contain only numbers.")
    if not all(math.isfinite(v) for v in df["contacts"]):
        raise ValueError("The 'contacts' column has an empty, infinite or invalid value.")
    if (df["contacts"] < 0).any():
        raise ValueError("The 'contacts' column cannot have negative values.")
    if df["period"].isna().any() or (df["period"].astype(str).str.strip() == "").any():
        raise ValueError("The 'period' column has an empty value.")
    if df["period"].duplicated().any():
        raise ValueError("There are duplicate periods in the CSV; each interval must appear once.")
    df["period"] = df["period"].astype(str).str.strip()
    return df
