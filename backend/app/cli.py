import argparse
import json
import logging
import sys

from . import db, generator, load, pipeline, quality


def main(argv=None):
    p = argparse.ArgumentParser(prog="pipeline")
    p.add_argument("--db", default=None, help="SQLite path (default data/warehouse.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate")
    g.add_argument("--orders", type=int, default=200)
    g.add_argument("--customers", type=int, default=50)
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--out", default="data/sample")

    c = sub.add_parser("load-customers"); c.add_argument("path")
    r = sub.add_parser("run"); r.add_argument("path")
    sub.add_parser("quality")
    rc = sub.add_parser("reconcile"); rc.add_argument("path")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.cmd == "generate":
        print(json.dumps(generator.generate(args.orders, args.customers, args.seed, args.out), indent=2))
        return 0

    if args.cmd == "run":
        summary = pipeline.run_pipeline(args.path, args.db)
        print(json.dumps(summary, indent=2))
        return 1 if summary["status"] == "FAILED" else 0

    conn = db.connect(args.db)
    try:
        if args.cmd == "load-customers":
            print(f"loaded {load.load_customers(conn, args.path)} customers")
            return 0
                if args.cmd == "reconcile":
            result = quality.reconcile_source(conn, args.path)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
        results = quality.run_checks(conn)
        print(json.dumps(results, indent=2))
        return 0 if all(x["passed"] for x in results) else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())