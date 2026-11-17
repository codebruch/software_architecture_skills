"""Fill the database with demo data.

    python3 scripts/seed.py                 # 50 customers, 200 orders
    python3 scripts/seed.py 2000 20000      # production-sized: customers, orders
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orderdesk import db  # noqa: E402


def main():
    customers = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    orders = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rng = random.Random(42)
    c = db.conn()
    c.execute("DELETE FROM order_items")
    c.execute("DELETE FROM orders")
    c.execute("DELETE FROM customers")
    for i in range(1, customers + 1):
        c.execute("INSERT INTO customers (id, name, email, vip) VALUES (?,?,?,?)",
                  (i, "Customer %04d" % i, "c%d@example.com" % i, 1 if rng.random() < 0.1 else 0))
    for n in range(orders):
        total = rng.randint(5_00, 400_00)
        c.execute(
            "INSERT INTO orders (id, customer_id, status, subtotal_cents, discount_cents, tax_cents,"
            " shipping_cents, total_cents, refunded_cents, charge_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("seed-%06d" % n, rng.randint(1, customers), "REFUNDED" if rng.random() < 0.03 else "PAID",
             total, 0, 0, 0, total, 0, "ch_seed_%06d" % n, "2025-01-01T00:00:00"),
        )
    c.commit()
    print("seeded", customers, "customers and", orders, "orders into", db.config.DB_PATH)


if __name__ == "__main__":
    main()
