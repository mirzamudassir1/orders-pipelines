HEADER = ["order_id", "customer_id", "order_ts", "amount", "currency", "status", "updated_at"]


def good_row(**over):
    base = {"order_id": "ORD-000001", "customer_id": "CUST-00001",
            "order_ts": "2025-03-01T10:00:00Z", "amount": "100.00", "currency": "USD",
            "status": "created", "updated_at": "2025-03-01T10:00:00Z"}
    base.update(over)
    return [base[c] for c in HEADER]