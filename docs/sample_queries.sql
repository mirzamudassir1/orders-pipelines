-- 1. Orders and revenue by status
SELECT status, COUNT(*) AS orders, ROUND(SUM(amount_usd_cents)/100.0, 2) AS revenue_usd
FROM fact_orders GROUP BY status ORDER BY status;

-- 2. Rejects by reason
SELECT reason_code, COUNT(*) AS rejected
FROM rejected_records GROUP BY reason_code ORDER BY rejected DESC;

-- 3. Orders whose status changed (history preserved)
SELECT order_id, COUNT(*) AS events
FROM order_status_history GROUP BY order_id HAVING COUNT(*) > 1 ORDER BY events DESC LIMIT 10;

-- 4. Run audit
SELECT run_id, status, input_rows, accepted_rows, rejected_rows, duplicate_rows, duration_sec
FROM pipeline_runs ORDER BY started_at;