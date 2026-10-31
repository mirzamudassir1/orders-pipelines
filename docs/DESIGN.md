# Design and trade-offs

- **SQLite and the standard csv module:** zero setup and fully reproducible. The trade-off is a single writer and no distributed scale.
- **Validate, then load in one transaction:** all-or-nothing per file keeps reruns safe. The trade-off is that a failure late in the run reprocesses the whole file.
- **Row problems are quarantined; structural problems fail the run:** a schema change should stop the line, while one bad row should not.
- **fact_orders holds the latest state; order_status_history holds the full event log:** history is preserved and nothing is silently overwritten.
- **Dedupe key is (order_id, updated_at):** the first occurrence wins. Later copies, in the same file or in a file loaded earlier (checked against history with one indexed lookup per row), are quarantined as DUPLICATE_EVENT.
- **Money is stored as integer cents and parsed with Decimal:** no float drift.
- **The generator writes expected.json separately from the input:** labels never leak into the data.
- **Optimization:** batched single-transaction writes. The benchmark compares them with per-row commits.