import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from . import db, ingest, load, transform, validate

log = logging.getLogger("pipeline")


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_dict(conn, run_id):
    return dict(conn.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)).fetchone())


def run_pipeline(source_file, db_path=None, now=None):
    source_file = Path(source_file)
    file_hash = ingest.file_sha256(source_file)      # FileNotFoundError if missing
    started = datetime.now(timezone.utc)
    now = now or started
    run_id = f"run_{started.strftime('%Y%m%dT%H%M%S%f')}_{file_hash[:8]}"
    name = source_file.name

    conn = db.connect(db_path)
    try:
        prior = conn.execute(
            "SELECT run_id FROM pipeline_runs WHERE file_hash = ? AND status = 'SUCCESS'",
            (file_hash,)).fetchone()
        if prior:
            conn.execute(
                "INSERT INTO pipeline_runs (run_id, source_file, file_hash, status, "
                "started_at, ended_at, failure_reason) VALUES (?,?,?,?,?,?,?)",
                (run_id, name, file_hash, "SKIPPED", _iso(started), _iso(started),
                 f"identical file already loaded in {prior['run_id']}"))
            log.info("run %s skipped (already loaded)", run_id)
            return _run_dict(conn, run_id)

        conn.execute(
            "INSERT INTO pipeline_runs (run_id, source_file, file_hash, status, started_at) "
            "VALUES (?,?,?,?,?)", (run_id, name, file_hash, "RUNNING", _iso(started)))
        log.info("run %s started for %s", run_id, name)

        t0 = time.perf_counter()
        input_rows = duplicates = 0
        try:
            known = {r[0] for r in conn.execute("SELECT customer_id FROM dim_customer")}
            events, rejects, seen = [], [], set()

            for line_no, row in ingest.iter_rows(source_file):
                input_rows += 1
                clean, rej = validate.validate_row(row, known, now)
                if rej:
                    rejects.append((line_no, rej[0], rej[1], row))
                    continue
                event = transform.to_event(clean)
                key = (event["order_id"], event["updated_at"])
                if key in seen:
                    duplicates += 1
                    rejects.append((line_no, "DUPLICATE_EVENT",
                                    "same order_id + updated_at already in batch", row))
                    continue
                seen.add(key)
                events.append(event)

            conn.execute("BEGIN")
            load.insert_rejects(conn, run_id, name, rejects)
            load.insert_history(conn, run_id, name, events)
            load.upsert_orders(conn, run_id, name, events)
            duration = time.perf_counter() - t0
            conn.execute(
                "UPDATE pipeline_runs SET status='SUCCESS', ended_at=?, input_rows=?, "
                "accepted_rows=?, rejected_rows=?, duplicate_rows=?, duration_sec=? "
                "WHERE run_id=?",
                (_iso(datetime.now(timezone.utc)), input_rows, len(events), len(rejects),
                 duplicates, round(duration, 4), run_id))
            conn.execute("COMMIT")
            log.info("run %s SUCCESS in=%d ok=%d rejected=%d", run_id,
                     input_rows, len(events), len(rejects))
        except Exception as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            conn.execute(
                "UPDATE pipeline_runs SET status='FAILED', ended_at=?, input_rows=?, "
                "duration_sec=?, failure_reason=? WHERE run_id=?",
                (_iso(datetime.now(timezone.utc)), input_rows,
                 round(time.perf_counter() - t0, 4), f"{type(exc).__name__}: {exc}", run_id))
            log.error("run %s FAILED: %s", run_id, exc)
        return _run_dict(conn, run_id)
    finally:
        conn.close()