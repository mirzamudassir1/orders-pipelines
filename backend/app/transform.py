from decimal import Decimal, ROUND_HALF_UP

from . import config
from .validate import fmt_ts


def to_event(clean):
    amount_cents = int((clean["amount"] * 100).to_integral_value(ROUND_HALF_UP))
    rate = config.FX_TO_USD[clean["currency"]]
    usd_cents = int((Decimal(amount_cents) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {
        "order_id": clean["order_id"],
        "customer_id": clean["customer_id"],
        "order_ts": fmt_ts(clean["order_ts"]),
        "order_date": clean["order_ts"].date().isoformat(),
        "amount_cents": amount_cents,
        "currency": clean["currency"],
        "amount_usd_cents": usd_cents,
        "status": clean["status"],
        "updated_at": fmt_ts(clean["updated_at"]),
    }