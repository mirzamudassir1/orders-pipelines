import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db, generator, load, pipeline  # noqa: E402


def end_to_end(n=100_000):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        generator.generate(n, 2000, 42, d)
        p = d / "bench.db"
        c = db.connect(p)
        load.load_customers(c, d / "customers.csv")
        c.close()
        t = time.perf_counter()
        s = pipeline.run_pipeline(d / "orders.csv", p)
        el = time.perf_counter() - t
        print(f"end-to-end: {n:,} rows in {el:.2f}s = {n / el:,.0f} rows/s | "
              f"accepted={s['accepted_rows']} rejected={s['rejected_rows']}")


def load_strategy(n=20_000):
    rows = [(f"ORD-{i:06d}", "paid") for i in range(n)]
    with tempfile.TemporaryDirectory() as d:
        c = sqlite3.connect(Path(d) / "a.db"); c.isolation_level = None
        c.execute("CREATE TABLE t (id TEXT PRIMARY KEY, s TEXT)")
        t = time.perf_counter()
        for r in rows:                                   # naive: commit per row
            c.execute("INSERT INTO t VALUES (?,?)", r)
        naive = time.perf_counter() - t
        c.close()

        c2 = sqlite3.connect(Path(d) / "b.db"); c2.isolation_level = None
        c2.execute("CREATE TABLE t (id TEXT PRIMARY KEY, s TEXT)")
        t = time.perf_counter()
        c2.execute("BEGIN"); c2.executemany("INSERT INTO t VALUES (?,?)", rows); c2.execute("COMMIT")
        batched = time.perf_counter() - t
        c2.close()
    print(f"per-row commit: {naive:.2f}s | batched single txn: {batched:.2f}s | "
          f"speedup x{naive / batched:.0f}")


if __name__ == "__main__":
    end_to_end()
    load_strategy()