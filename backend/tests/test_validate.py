from datetime import datetime, timezone

import pytest

from app.validate import validate_row

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
KNOWN = {"CUST-00001"}


def row(**over):
    base = {"order_id": "ORD-000001", "customer_id": "CUST-00001",
            "order_ts": "2025-03-01T10:00:00Z", "amount": "100.00", "currency": "USD",
            "status": "created", "updated_at": "2025-03-01T10:00:00Z"}
    base.update(over)
    return base


def code(r):
    _, rej = validate_row(r, KNOWN, NOW)
    return None if rej is None else rej[0]


def test_valid_row_passes():
    clean, rej = validate_row(row(), KNOWN, NOW)
    assert rej is None and clean["order_id"] == "ORD-000001"


@pytest.mark.parametrize("amount,expected", [
    ("0.01", None), ("100000.00", None),                 # boundaries (inclusive)
    ("0.00", "AMOUNT_OUT_OF_RANGE"), ("0", "AMOUNT_OUT_OF_RANGE"),
    ("-1", "AMOUNT_OUT_OF_RANGE"), ("100000.01", "AMOUNT_OUT_OF_RANGE"),
    ("abc", "INVALID_AMOUNT"), ("NaN", "INVALID_AMOUNT"),
    ("12.345", "INVALID_AMOUNT"),
])
def test_amount_boundaries(amount, expected):
    assert code(row(amount=amount)) == expected


@pytest.mark.parametrize("col", ["order_id", "customer_id", "order_ts", "amount",
                                 "currency", "status", "updated_at"])
def test_missing_required_field(col):
    assert code(row(**{col: ""})) == "MISSING_REQUIRED_FIELD"


def test_malformed_rows():
    assert code({**row(), None: ["extra"]}) == "MALFORMED_ROW"      # too many fields
    short = row(); short["updated_at"] = None
    assert code(short) == "MALFORMED_ROW"                           # too few fields


def test_other_rules():
    assert code(row(order_id="X-1")) == "INVALID_ORDER_ID"
    assert code(row(status="delivered")) == "INVALID_STATUS"
    assert code(row(currency="GBP")) == "INVALID_CURRENCY"
    assert code(row(order_ts="2025-13-45")) == "INVALID_TIMESTAMP"
    assert code(row(order_ts="2999-01-01T00:00:00Z", updated_at="2999-01-01T00:00:00Z")) == "FUTURE_TIMESTAMP"
    assert code(row(updated_at="2025-03-01T09:00:00Z")) == "TIMESTAMP_ORDER"
    assert code(row(customer_id="CUST-99999")) == "INVALID_REFERENCE"


def test_normalisation_and_timezone_to_utc():
    clean, rej = validate_row(row(status=" PAID ", currency="usd",
                                  order_ts="2025-03-01T23:30:00-05:00",
                                  updated_at="2025-03-01T23:30:00-05:00"), KNOWN, NOW)
    assert rej is None
    assert clean["status"] == "paid" and clean["currency"] == "USD"
    assert clean["order_ts"] == datetime(2025, 3, 2, 4, 30, tzinfo=timezone.utc)