import csv
import hashlib
import logging

from . import config

log = logging.getLogger("pipeline")


class SchemaError(Exception):
    pass


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_rows(path):
    """Yield (line_no, row_dict). Raises SchemaError on header problems."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = [h.strip() for h in (reader.fieldnames or [])]
        if not header:
            raise SchemaError("file is empty or has no header row")
        missing = [c for c in config.REQUIRED_COLUMNS if c not in header]
        if missing:
            raise SchemaError(f"missing required columns: {missing}")
        extra = [c for c in header if c not in config.REQUIRED_COLUMNS]
        if extra:
            log.warning("ignoring unexpected columns: %s", extra)
        reader.fieldnames = header
        for row in reader:
            yield reader.line_num, row