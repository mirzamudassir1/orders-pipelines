from app import db, generator, load, pipeline
from helpers import good_row


def test_upper_amount_boundary_is_inclusive(conn, db_path, make_csv):
    # regression: an early version used `<` and rejected 100000.00
    s = pipeline.run_pipeline(make_csv("b.csv", [
        good_row(amount="100000.00"),
        good_row(order_id="ORD-000002", amount="0.01")]), db_path)
    assert s["accepted_rows"] == 2


def test_equal_timestamp_event_does_not_flip_state(conn, db_path, make_csv):
    pipeline.run_pipeline(make_csv("a.csv", [good_row(status="paid")]), db_path)
    pipeline.run_pipeline(make_csv("b.csv", [good_row(status="refunded")]), db_path)  # same updated_at
    assert conn.execute("SELECT status FROM fact_orders").fetchone()[0] == "paid"


def test_generator_same_seed_same_bytes(tmp_path):
    generator.generate(500, 20, 5, tmp_path / "a")
    generator.generate(500, 20, 5, tmp_path / "b")
    assert (tmp_path / "a" / "orders.csv").read_bytes() == (tmp_path / "b" / "orders.csv").read_bytes()


def _snapshot(path):
    c = db.connect(path)
    rows = c.execute("SELECT order_id, customer_id, order_ts, amount_cents, amount_usd_cents, "
                     "status, updated_at FROM fact_orders ORDER BY order_id").fetchall()
    c.close()
    return [tuple(r) for r in rows]


def test_pipeline_output_is_deterministic(tmp_path):
    generator.generate(1000, 30, 99, tmp_path / "g")
    snaps = []
    for i in range(2):
        p = tmp_path / f"w{i}.db"
        c = db.connect(p)
        load.load_customers(c, tmp_path / "g" / "customers.csv")
        c.close()
        pipeline.run_pipeline(tmp_path / "g" / "orders.csv", p)
        snaps.append(_snapshot(p))
    assert snaps[0] == snaps[1] and len(snaps[0]) > 0