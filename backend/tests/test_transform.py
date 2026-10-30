from datetime import datetime, timezone
from decimal import Decimal

from app.transform import to_event


def clean(**over):
    ts = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    base = {"order_id": "ORD-000001", "customer_id": "CUST-00001", "order_ts": ts,
            "updated_at": ts, "amount": Decimal("10.01"), "currency": "EUR", "status": "paid"}
    base.update(over)
    return base


def test_cents_and_usd_conversion():
    e = to_event(clean())
    assert e["amount_cents"] == 1001 and e["amount_usd_cents"] == 1081   # 1001 * 1.08


def test_inr_and_half_up_rounding():
    assert to_event(clean(amount=Decimal("1000.00"), currency="INR"))["amount_usd_cents"] == 1200
    assert to_event(clean(amount=Decimal("0.50"), currency="INR"))["amount_usd_cents"] == 1  # 0.6 -> 1


def test_iso_formats_and_order_date():
    e = to_event(clean())
    assert e["order_ts"] == "2025-03-01T10:00:00Z" and e["order_date"] == "2025-03-01"


def test_deterministic():
    assert to_event(clean()) == to_event(clean())