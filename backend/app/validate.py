import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from . import config

_ORDER_ID_RE = re.compile(config.ORDER_ID_PATTERN)


def parse_ts(value):
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)              # raises ValueError
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fmt_ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_row(row, known_customers, now=None):
    """Return (clean_dict, None) or (None, (reason_code, detail))."""
    now = now or datetime.now(timezone.utc)

    if None in row or any(v is None for v in row.values()):
        return None, ("MALFORMED_ROW", "column count does not match header")

    r = {k: (v or "").strip() for k, v in row.items()}

    missing = [c for c in config.REQUIRED_COLUMNS if not r.get(c)]
    if missing:
        return None, ("MISSING_REQUIRED_FIELD", ",".join(missing))

    if not _ORDER_ID_RE.match(r["order_id"]):
        return None, ("INVALID_ORDER_ID", r["order_id"])

    status = r["status"].lower()
    if status not in config.VALID_STATUSES:
        return None, ("INVALID_STATUS", r["status"])

    currency = r["currency"].upper()
    if currency not in config.FX_TO_USD:
        return None, ("INVALID_CURRENCY", r["currency"])

    try:
        amount = Decimal(r["amount"])
    except InvalidOperation:
        return None, ("INVALID_AMOUNT", r["amount"])
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        return None, ("INVALID_AMOUNT", r["amount"])
    if not (config.MIN_AMOUNT <= amount <= config.MAX_AMOUNT):
        return None, ("AMOUNT_OUT_OF_RANGE", r["amount"])

    try:
        order_ts = parse_ts(r["order_ts"])
        updated_at = parse_ts(r["updated_at"])
    except ValueError:
        return None, ("INVALID_TIMESTAMP", f'{r["order_ts"]} / {r["updated_at"]}')
    if order_ts > now or updated_at > now:
        return None, ("FUTURE_TIMESTAMP", f'{r["order_ts"]} / {r["updated_at"]}')
    if updated_at < order_ts:
        return None, ("TIMESTAMP_ORDER", "updated_at is before order_ts")

    if r["customer_id"] not in known_customers:
        return None, ("INVALID_REFERENCE", r["customer_id"])

    return {
        "order_id": r["order_id"], "customer_id": r["customer_id"],
        "order_ts": order_ts, "updated_at": updated_at,
        "amount": amount, "currency": currency, "status": status,
    }, None