import csv

import pytest

from app import db
from helpers import HEADER


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def conn(db_path):
    c = db.connect(db_path)
    c.execute("INSERT INTO dim_customer VALUES ('CUST-00001','Alice','IN'),('CUST-00002','Bob','US')")
    yield c
    c.close()


@pytest.fixture
def make_csv(tmp_path):
    def _make(name, rows, header=HEADER):
        p = tmp_path / name
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if header is not None:
                w.writerow(header)
            w.writerows(rows)
        return p
    return _make