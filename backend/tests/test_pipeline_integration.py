import pytest

from app import load, pipeline
from helpers import HEADER, good_row


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_happy_path(conn, db_path, make_csv):
    f = make_csv("a.csv", [good_row(), good_row(order_id="ORD-000002", customer_id="CUST-00002")])
    s = pipeline.run_pipeline(f, db_path)
    assert s["status"] == "SUCCESS"
    assert (s["input_rows"], s["accepted_rows"], s["rejected_rows"]) == (2, 2, 0)
    assert count(conn, "fact_orders") == 2 and count(conn, "order_status_history") == 2


def test_empty_batch_header_only(conn, db_path, make_csv):
    s = pipeline.run_pipeline(make_csv("e.csv", []), db_path)
    assert s["status"] == "SUCCESS" and s["input_rows"] == 0
    assert count(conn, "fact_orders") == 0


def test_empty_file_no_header_fails(conn, db_path, make_csv):
    s = pipeline.run_pipeline(make_csv("e.csv", [], header=None), db_path)
    assert s["status"] == "FAILED" and "empty" in s["failure_reason"]


def test_schema_change_missing_column_fails(conn, db_path, make_csv):
    header = [c for c in HEADER if c != "currency"]
    s = pipeline.run_pipeline(make_csv("s.csv", [["ORD-000001", "CUST-00001", "x", "1", "paid", "x"]],
                                       header=header), db_path)
    assert s["status"] == "FAILED" and "currency" in s["failure_reason"]
    assert count(conn, "fact_orders") == 0


def test_extra_column_is_ignored(conn, db_path, make_csv):
    f = make_csv("x.csv", [good_row() + ["note"]], header=HEADER + ["extra"])
    assert pipeline.run_pipeline(f, db_path)["status"] == "SUCCESS"
    assert count(conn, "fact_orders") == 1


def test_rejects_are_traceable_and_reconcile(conn, db_path, make_csv):
    f = make_csv("r.csv", [
        good_row(),
        good_row(order_id="ORD-000002", customer_id="NOPE"),     # invalid reference
        good_row(order_id="ORD-000003", customer_id=""),         # missing field
        ["ORD-000004", "CUST-00001"],                            # malformed (short)
    ])
    s = pipeline.run_pipeline(f, db_path)
    assert s["input_rows"] == s["accepted_rows"] + s["rejected_rows"] == 4
    rows = conn.execute("SELECT line_no, reason_code, raw_record, source_file, run_id "
                        "FROM rejected_records ORDER BY line_no").fetchall()
    assert [r["line_no"] for r in rows] == [3, 4, 5]
    assert [r["reason_code"] for r in rows] == ["INVALID_REFERENCE", "MISSING_REQUIRED_FIELD", "MALFORMED_ROW"]
    assert all(r["source_file"] == "r.csv" and r["run_id"] == s["run_id"] for r in rows)


def test_duplicates_in_batch(conn, db_path, make_csv):
    s = pipeline.run_pipeline(make_csv("d.csv", [good_row(), good_row()]), db_path)
    assert (s["accepted_rows"], s["duplicate_rows"], s["rejected_rows"]) == (1, 1, 1)
    assert conn.execute("SELECT reason_code FROM rejected_records").fetchone()[0] == "DUPLICATE_EVENT"


def test_rerun_same_file_is_skipped_and_creates_no_duplicates(conn, db_path, make_csv):
    f = make_csv("a.csv", [good_row()])
    pipeline.run_pipeline(f, db_path)
    s2 = pipeline.run_pipeline(f, db_path)
    assert s2["status"] == "SKIPPED"
    assert count(conn, "fact_orders") == 1 and count(conn, "order_status_history") == 1


def test_overlapping_files_are_idempotent(conn, db_path, make_csv):
    a = make_csv("a.csv", [good_row()])
    b = make_csv("b.csv", [good_row(), good_row(order_id="ORD-000002")])
    pipeline.run_pipeline(a, db_path)
    pipeline.run_pipeline(b, db_path)
    assert count(conn, "fact_orders") == 2 and count(conn, "order_status_history") == 2


def test_late_arriving_event_does_not_overwrite_newer_state(conn, db_path, make_csv):
    pipeline.run_pipeline(make_csv("a.csv", [good_row(status="paid", updated_at="2025-03-01T12:00:00Z")]), db_path)
    pipeline.run_pipeline(make_csv("b.csv", [good_row(status="created", updated_at="2025-03-01T10:00:00Z")]), db_path)
    assert conn.execute("SELECT status FROM fact_orders").fetchone()[0] == "paid"
    assert count(conn, "order_status_history") == 2          # history preserved


def test_out_of_order_within_batch(conn, db_path, make_csv):
    f = make_csv("o.csv", [good_row(status="shipped", updated_at="2025-03-02T10:00:00Z"), good_row()])
    pipeline.run_pipeline(f, db_path)
    assert conn.execute("SELECT status FROM fact_orders").fetchone()[0] == "shipped"


def test_partial_failure_rolls_back_then_retry_succeeds(conn, db_path, make_csv, monkeypatch):
    f = make_csv("p.csv", [good_row(), good_row(order_id="ORD-000002", customer_id="NOPE")])

    def boom(*a, **k):
        raise RuntimeError("disk full")

    with monkeypatch.context() as m:
        m.setattr(load, "upsert_orders", boom)
        s = pipeline.run_pipeline(f, db_path)
    assert s["status"] == "FAILED" and "disk full" in s["failure_reason"]
    assert count(conn, "fact_orders") == 0
    assert count(conn, "rejected_records") == 0 and count(conn, "order_status_history") == 0

    s2 = pipeline.run_pipeline(f, db_path)                  # retry
    assert s2["status"] == "SUCCESS"
    assert count(conn, "fact_orders") == 1 and count(conn, "rejected_records") == 1


def test_missing_file_raises(tmp_path, db_path):
    with pytest.raises(FileNotFoundError):
        pipeline.run_pipeline(tmp_path / "nope.csv", db_path)