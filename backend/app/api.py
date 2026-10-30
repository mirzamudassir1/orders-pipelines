import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from . import config, db, pipeline, quality

app = FastAPI(title="Orders Pipeline API")


def _with_conn(fn):
    conn = db.connect()
    try:
        return fn(conn)
    finally:
        conn.close()


@app.get("/api/runs")
def runs():
    return _with_conn(lambda c: [dict(r) for r in c.execute(
        "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 50")])


@app.get("/api/summary")
def summary():
    return _with_conn(quality.summary)


@app.get("/api/quality")
def quality_checks():
    return _with_conn(quality.run_checks)


@app.get("/api/rejects")
def rejects(run_id: Optional[str] = None, limit: int = 200):
    limit = max(1, min(limit, 1000))
    def q(c):
        if run_id:
            cur = c.execute("SELECT * FROM rejected_records WHERE run_id=? ORDER BY line_no LIMIT ?",
                            (run_id, limit))
        else:
            cur = c.execute("SELECT * FROM rejected_records ORDER BY reject_id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur]
    return _with_conn(q)


@app.post("/api/run")
def run(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.UPLOAD_DIR / Path(file.filename).name
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return pipeline.run_pipeline(dest)


if config.FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")