## Results

- Tests: 43 passed (`docs/test_results.txt`)
- Sample run: input 200, accepted 174, rejected 26, duplicates 2, matching `data/sample/expected.json`
- Quality checks: 10 of 10 pass (`docs/reconciliation.txt`)
- Source-to-target aggregates reconcile: 168 orders, 52,442,529 total amount cents, 39,650,504 total USD cents (`docs/reconciliation_aggregates.txt`)
- Benchmark (100,000 rows, seed 42, local Windows machine): 11.43 s end-to-end, about 8,751 rows/s (`docs/benchmark_results.txt`)
- Optimization: all writes are batched with `executemany` inside one transaction. In an isolated micro-benchmark of 20,000 inserts, a commit per row took 62.06 s versus 0.03 s for one batched transaction. The gap is exaggerated by per-commit disk syncs on Windows, so the exact ratio varies by machine.
- Next optimization: stream the file in chunks of about 10k rows instead of holding all events in memory.
<br>
<br>
<br>
<br>
<br>
<br>
<br>

![Dashboard](./docs/dashboard.png)
