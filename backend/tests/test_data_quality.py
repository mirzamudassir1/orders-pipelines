import json

from app import db, generator, load, pipeline, quality


def test_generated_dataset_matches_labels_and_quality_checks_pass(tmp_path, db_path):
    out = tmp_path / "gen"
    generator.generate(2000, 50, 7, out)
    expected = json.loads((out / "expected.json").read_text())

    conn = db.connect(db_path)
    load.load_customers(conn, out / "customers.csv")
    s = pipeline.run_pipeline(out / "orders.csv", db_path)

    assert s["status"] == "SUCCESS"
    assert s["input_rows"] == expected["input_rows"]
    assert s["accepted_rows"] == expected["accepted_rows"]
    got = {r["reason_code"]: r["n"] for r in conn.execute(
        "SELECT reason_code, COUNT(*) AS n FROM rejected_records GROUP BY reason_code")}
    assert got == expected["rejected_by_code"]
    assert conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0] == expected["distinct_orders"]
    assert [c for c in quality.run_checks(conn) if not c["passed"]] == []