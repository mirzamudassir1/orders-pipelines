import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.getenv("PIPELINE_DB", DATA_DIR / "warehouse.db"))
UPLOAD_DIR = DATA_DIR / "uploads"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

REQUIRED_COLUMNS = ["order_id", "customer_id", "order_ts", "amount",
                    "currency", "status", "updated_at"]
ORDER_ID_PATTERN = r"^ORD-\d{6,}$"
VALID_STATUSES = frozenset({"created", "paid", "shipped", "cancelled", "refunded"})
FX_TO_USD = {"USD": Decimal("1.00"), "EUR": Decimal("1.08"), "INR": Decimal("0.012")}
MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("100000.00")