import csv
import json

UPSERT_ORDERS = """
INSERT INTO fact_orders (order_id, customer_id, order_ts, order_date, amount_cents,
  currency, amount_usd_cents, status, updated_at, source_file, run_id)
VALUES (:order_id, :customer_id, :order_ts, :order_date, :amount_cents,
  :currency, :amount_usd_cents, :status, :updated_at, :source_file, :run_id)
ON CONFLICT(order_id) DO UPDATE SET
  customer_id=excluded.customer_id, order_ts=excluded.order_ts,
  order_date=excluded.order_date, amount_cents=excluded.amount_cents,
  currency=excluded.currency, amount_usd_cents=excluded.amount_usd_cents,
  status=excluded.status, updated_at=excluded.updated_at,
  source_file=excluded.source_file, run_id=excluded.run_id
WHERE excluded.updated_at > fact_orders.updated_at
"""


def load_customers(conn, path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for line_no, r in enumerate(csv.DictReader(f), start=2):
            vals = tuple((r.get(c) or "").strip()
                         for c in ("customer_id", "customer_name", "country"))
            if not all(vals):
                raise ValueError(f"{path}:{line_no} invalid customer row")
            rows.append(vals)
    conn.execute("BEGIN")
    try:
        conn.executemany(
            "INSERT INTO dim_customer (customer_id, customer_name, country) VALUES (?,?,?) "
            "ON CONFLICT(customer_id) DO UPDATE SET "
            "customer_name=excluded.customer_name, country=excluded.country", rows)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return len(rows)


def insert_rejects(conn, run_id, source_file, rejects):
    conn.executemany(
        "INSERT INTO rejected_records (run_id, source_file, line_no, reason_code, "
        "reason_detail, raw_record) VALUES (?,?,?,?,?,?)",
        [(run_id, source_file, line_no, code, detail,
          json.dumps(row, default=str, ensure_ascii=False))
         for line_no, code, detail, row in rejects])


def insert_history(conn, run_id, source_file, events):
    conn.executemany(
        "INSERT OR IGNORE INTO order_status_history "
        "(order_id, status, updated_at, run_id, source_file) VALUES (?,?,?,?,?)",
        [(e["order_id"], e["status"], e["updated_at"], run_id, source_file) for e in events])


def upsert_orders(conn, run_id, source_file, events):
    conn.executemany(
        UPSERT_ORDERS,
        [{**e, "run_id": run_id, "source_file": source_file} for e in events])