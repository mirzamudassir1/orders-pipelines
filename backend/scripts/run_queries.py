import sqlite3
import sys
from pathlib import Path

db_path, sql_path = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(db_path)
for stmt in Path(sql_path).read_text().split(";"):
    if not stmt.strip():
        continue
    print("--", stmt.strip().splitlines()[0].lstrip("- "))
    cur = conn.execute(stmt)
    print(" | ".join(d[0] for d in cur.description))
    for row in cur.fetchall():
        print(" | ".join(str(v) for v in row))
    print()
conn.close()