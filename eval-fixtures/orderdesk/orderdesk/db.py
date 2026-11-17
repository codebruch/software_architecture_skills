import sqlite3
import threading

from orderdesk import config

_conn = None
_lock = threading.Lock()


def conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, vip INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, customer_id INTEGER NOT NULL, status TEXT NOT NULL,
                subtotal_cents INTEGER, discount_cents INTEGER, tax_cents INTEGER,
                shipping_cents INTEGER, total_cents INTEGER, refunded_cents INTEGER DEFAULT 0,
                charge_id TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS order_items (
                order_id TEXT, sku TEXT, qty INTEGER, unit_cents INTEGER
            );
            """
        )
    return _conn


def get_customer(customer_id):
    return conn().execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()


def find_orders_by_customer_name(name):
    sql = "SELECT o.* FROM orders o JOIN customers c ON c.id = o.customer_id WHERE c.name LIKE '%" + name + "%'"
    return conn().execute(sql).fetchall()


def get_order(order_id):
    return conn().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()


def all_orders():
    return conn().execute("SELECT * FROM orders").fetchall()


def all_customers():
    return conn().execute("SELECT * FROM customers").fetchall()
