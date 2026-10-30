import sqlite3
from pathlib import Path

from . import config

DDL = """
CREATE TABLE IF NOT EXISTS dim_customer (
  customer_id   TEXT PRIMARY KEY,
  customer_name TEXT NOT NULL,
  country       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_orders (
  order_id         TEXT PRIMARY KEY,
  customer_id      TEXT NOT NULL REFERENCES dim_customer(customer_id),
  order_ts         TEXT NOT NULL,
  order_date       TEXT NOT NULL,
  amount_cents     INTEGER NOT NULL CHECK (amount_cents > 0),
  currency         TEXT NOT NULL,
  amount_usd_cents INTEGER NOT NULL,
  status           TEXT NOT NULL,
  updated_at       TEXT NOT NULL,
  source_file      TEXT NOT NULL,
  run_id           TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_status_history (
  order_id    TEXT NOT NULL,
  status      TEXT NOT NULL,
  updated_at  TEXT NOT NULL,
  run_id      TEXT NOT NULL,
  source_file TEXT NOT NULL,
  PRIMARY KEY (order_id, updated_at)
);
CREATE TABLE IF NOT EXISTS rejected_records (
  reject_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id        TEXT NOT NULL,
  source_file   TEXT NOT NULL,
  line_no       INTEGER NOT NULL,
  reason_code   TEXT NOT NULL,
  reason_detail TEXT,
  raw_record    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id         TEXT PRIMARY KEY,
  source_file    TEXT NOT NULL,
  file_hash      TEXT NOT NULL,
  status         TEXT NOT NULL,
  started_at     TEXT NOT NULL,
  ended_at       TEXT,
  input_rows     INTEGER DEFAULT 0,
  accepted_rows  INTEGER DEFAULT 0,
  rejected_rows  INTEGER DEFAULT 0,
  duplicate_rows INTEGER DEFAULT 0,
  duration_sec   REAL,
  failure_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_rejects_run ON rejected_records(run_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON fact_orders(customer_id);
"""


def connect(db_path=None):
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.isolation_level = None          # autocommit; we use explicit BEGIN/COMMIT
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    return conn