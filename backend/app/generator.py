import csv
import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATUSES = ["created", "paid", "shipped", "cancelled", "refunded"]
CURRENCIES = ["USD", "EUR", "INR"]
COUNTRIES = ["IN", "US", "DE", "GB", "AE"]
BASE = datetime(2025, 1, 1, tzinfo=timezone.utc)
HEADER = ["order_id", "customer_id", "order_ts", "amount", "currency", "status", "updated_at"]


def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate(n_orders, n_customers, seed, out_dir):
    rng = random.Random(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    customers = [f"CUST-{i:05d}" for i in range(1, n_customers + 1)]
    with open(out_dir / "customers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "customer_name", "country"])
        for c in customers:
            w.writerow([c, f"Customer {c[-5:]}", rng.choice(COUNTRIES)])

    seq = 0

    def new_row():
        nonlocal seq
        seq += 1
        ts = fmt(BASE + timedelta(seconds=rng.randint(0, 364 * 86400)))
        if rng.random() < 0.01:                       # boundary values
            amount = rng.choice([0.01, 100000.00])
        else:
            amount = round(rng.uniform(1, 5000), 2)
        return [f"ORD-{seq:06d}", rng.choice(customers), ts, f"{amount:.2f}",
                rng.choice(CURRENCIES), rng.choice(STATUSES), ts]

    kinds = ["valid", "update", "duplicate", "missing", "bad_amount",
             "bad_status", "bad_ref", "bad_ts", "malformed"]
    weights = [84, 4, 2, 2, 2, 2, 2, 1, 1]

    rows, pool, updatable = [], [], []
    expected = Counter()
    accepted = distinct = 0

    for _ in range(n_orders):
        kind = rng.choices(kinds, weights)[0]
        if kind == "update" and not updatable:
            kind = "valid"
        if kind == "duplicate" and not pool:
            kind = "valid"

        if kind == "valid":
            r = new_row()
            pool.append(r); updatable.append(r)
            accepted += 1; distinct += 1
        elif kind == "update":                         # later event for an existing order
            base = updatable.pop(rng.randrange(len(updatable)))
            ts = datetime.fromisoformat(base[2].replace("Z", "+00:00"))
            r = list(base)
            r[5] = rng.choice(STATUSES)
            r[6] = fmt(ts + timedelta(hours=rng.randint(1, 48)))
            pool.append(r); accepted += 1
        elif kind == "duplicate":
            r = list(rng.choice(pool))
            expected["DUPLICATE_EVENT"] += 1
        elif kind == "missing":
            r = new_row(); r[1] = ""
            expected["MISSING_REQUIRED_FIELD"] += 1
        elif kind == "bad_amount":
            r = new_row()
            value, code = rng.choice([
                ("abc", "INVALID_AMOUNT"), ("12.345", "INVALID_AMOUNT"),
                ("-5.00", "AMOUNT_OUT_OF_RANGE"), ("0", "AMOUNT_OUT_OF_RANGE"),
                ("100000.01", "AMOUNT_OUT_OF_RANGE")])
            r[3] = value
            expected[code] += 1
        elif kind == "bad_status":
            r = new_row(); r[5] = "delivered"
            expected["INVALID_STATUS"] += 1
        elif kind == "bad_ref":
            r = new_row(); r[1] = f"CUST-{n_customers + 1000:05d}"
            expected["INVALID_REFERENCE"] += 1
        elif kind == "bad_ts":
            r = new_row(); r[2] = "2025-13-45"
            expected["INVALID_TIMESTAMP"] += 1
        else:                                          # malformed: extra field
            r = new_row() + ["unexpected_extra"]
            expected["MALFORMED_ROW"] += 1
        rows.append(r)

    rng.shuffle(rows)                                  # out-of-order / late arrival

    with open(out_dir / "orders.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)

    meta = {
        "seed": seed, "input_rows": n_orders, "accepted_rows": accepted,
        "rejected_rows": sum(expected.values()), "distinct_orders": distinct,
        "rejected_by_code": dict(expected),
    }
    assert meta["accepted_rows"] + meta["rejected_rows"] == n_orders
    (out_dir / "expected.json").write_text(json.dumps(meta, indent=2))
    return meta