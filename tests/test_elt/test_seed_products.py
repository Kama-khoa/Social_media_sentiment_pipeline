import csv
from collections import Counter
from pathlib import Path


def test_seed_products_contains_500_unique_sample_products():
    csv_path = Path(__file__).parents[2] / "elt" / "seed_data" / "seed_products.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 500
    assert len({row["product_id"] for row in rows}) == 500
    assert Counter(row["category"] for row in rows) == {
        "Điện thoại": 250,
        "Laptop": 150,
        "Tai nghe": 100,
    }
