"""Tests for the demand CSV validation."""

import pandas as pd
import pytest

from src.demand import validate_demand


def df_ok() -> pd.DataFrame:
    return pd.DataFrame({"period": ["08:00", "08:30"], "contacts": [42, 58]})


def test_valid_csv():
    df = validate_demand(df_ok())
    assert list(df.columns) == ["period", "contacts"]
    assert len(df) == 2


def test_missing_column():
    with pytest.raises(ValueError, match="columns"):
        validate_demand(pd.DataFrame({"period": ["08:00"]}))


def test_empty():
    with pytest.raises(ValueError, match="no data rows"):
        validate_demand(pd.DataFrame({"period": [], "contacts": []}))


def test_non_numeric():
    with pytest.raises(ValueError, match="only numbers"):
        validate_demand(pd.DataFrame({"period": ["08:00"], "contacts": ["lots"]}))


def test_non_finite():
    for bad in [float("inf"), float("-inf"), float("nan")]:
        with pytest.raises(ValueError, match="empty, infinite or invalid"):
            validate_demand(pd.DataFrame({"period": ["08:00"], "contacts": [bad]}))


def test_negative():
    with pytest.raises(ValueError, match="negative"):
        validate_demand(pd.DataFrame({"period": ["08:00"], "contacts": [-5]}))


def test_zero_is_valid():
    # An interval with no demand is legitimate: the model answers 0 agents.
    df = validate_demand(pd.DataFrame({"period": ["03:00"], "contacts": [0]}))
    assert df["contacts"].iloc[0] == 0


def test_duplicate_period():
    with pytest.raises(ValueError, match="duplicate"):
        validate_demand(pd.DataFrame({"period": ["08:00", "08:00"], "contacts": [1, 2]}))


def test_empty_period():
    with pytest.raises(ValueError, match="period"):
        validate_demand(pd.DataFrame({"period": [" "], "contacts": [10]}))
