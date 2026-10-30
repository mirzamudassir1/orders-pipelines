from . import config


def run_checks(conn):
    statuses = sorted(config.VALID_STATUSES)
    ph = ",".join("?" * len(statuses))
    max_cents = int(config.MAX_AMOUNT * 100)
    specs = [
        ("unique_order_id",
         "SELECT COUNT(*) FROM (SELECT order_id FROM fact_orders GROUP BY order_id HAVING COUNT(*) > 1)",
         [], "order_id is unique in fact_orders"),
        ("referential_integrity",
         "SELECT COUNT(*) FROM fact_orders o LEFT JOIN dim_customer c USING (customer_id) "
         "WHERE c.customer_id IS NULL",
         [], "every order points to an existing customer"),
        ("no_blank_required",
         "SELECT COUNT(*) FROM fact_orders WHERE TRIM(customer_id)='' OR TRIM(status)='' OR TRIM(currency)=''",
         [], "no blank required fields"),
        ("amount_in_range",
         f"SELECT COUNT(*) FROM fact_orders WHERE amount_cents < 1 OR amount_cents > {max_cents}",
         [], "amounts within business limits"),
        ("valid_status",
         f"SELECT COUNT(*) FROM fact_orders WHERE status NOT IN ({ph})",
         statuses, "status is one of the allowed values"),
        ("orders_have_history",
         "SELECT COUNT(*) FROM fact_orders f WHERE NOT EXISTS "
         "(SELECT 1 FROM order_status_history h WHERE h.order_id = f.order_id)",
         [], "each order has at least one history event"),
        ("fact_equals_latest_history",
         "SELECT COUNT(*) FROM fact_orders f WHERE f.updated_at <> "
         "(SELECT MAX(updated_at) FROM order_status_history h WHERE h.order_id = f.order_id)",
         [], "fact_orders holds the latest event per order"),
        ("run_counts_reconcile",
         "SELECT COUNT(*) FROM pipeline_runs WHERE status='SUCCESS' "
         "AND input_rows <> accepted_rows + rejected_rows",
         [], "input = accepted + rejected for every successful run"),
        ("rejects_traceable",
         "SELECT COUNT(*) FROM rejected_records WHERE run_id NOT IN (SELECT run_id FROM pipeline_runs)",
         [], "every reject links to a run"),
        ("reject_totals_reconcile",
         "SELECT ABS((SELECT COALESCE(SUM(rejected_rows),0) FROM pipeline_runs WHERE status='SUCCESS') "
         "- (SELECT COUNT(*) FROM rejected_records))",
         [], "run-level reject counts match stored reject rows"),
    ]
    results = []
    for name, sql, params, desc in specs:
        n = conn.execute(sql, params).fetchone()[0]
        results.append({"check": name, "passed": n == 0, "violations": n, "description": desc})
    return results


def summary(conn):
    by_status = [dict(r) for r in conn.execute(
        "SELECT status, COUNT(*) AS orders, ROUND(SUM(amount_usd_cents)/100.0, 2) AS revenue_usd "
        "FROM fact_orders GROUP BY status ORDER BY status")]
    rejects = [dict(r) for r in conn.execute(
        "SELECT reason_code, COUNT(*) AS rejected FROM rejected_records "
        "GROUP BY reason_code ORDER BY rejected DESC")]
    return {"orders_by_status": by_status, "rejects_by_reason": rejects}