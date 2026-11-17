import unittest
from unittest import mock

from orderdesk import cache, config, db, payments, service


class CreateOrderCharacterization(unittest.TestCase):
    """Pins the current behavior of service.create_order (orderdesk/service.py:12)."""

    def setUp(self):
        config.DB_PATH = ":memory:"
        db._conn = None
        cache._customers.clear()
        c = db.conn()
        c.execute("INSERT INTO customers (id, name, email, vip) VALUES (1, 'Ada', 'ada@example.com', 0)")
        c.execute("INSERT INTO customers (id, name, email, vip) VALUES (2, 'Vip', 'vip@example.com', 1)")
        c.commit()
        self.addCleanup(c.close)
        patcher = mock.patch.object(payments, "_post", return_value={"id": "ch_test"})
        self.post = patcher.start()
        self.addCleanup(patcher.stop)
        publish = mock.patch.object(service.events, "publish")
        self.publish = publish.start()
        self.addCleanup(publish.stop)

    def order(self, customer_id=1, coupon=None, items=None):
        payload = {"customer_id": customer_id, "card_number": "4111",
                   "items": items or [{"sku": "a", "qty": 3, "unit_cents": 333}]}
        if coupon:
            payload["coupon"] = coupon
        return service.create_order(payload)

    def test_small_order_pays_shipping_and_truncated_tax(self):
        result = self.order()
        # characterizes current behavior; suspected bug: 19% of 999 is 189.81 and is truncated, not rounded
        self.assertEqual(result["tax_cents"], 189)
        self.assertEqual(result["shipping_cents"], 490)
        self.assertEqual(result["total_cents"], 1678)

    def test_bulk_discount_from_ten_items(self):
        result = self.order(items=[{"sku": "a", "qty": 10, "unit_cents": 1000}])
        self.assertEqual(result["discount_cents"], 500)
        self.assertEqual(result["shipping_cents"], 0)
        self.assertEqual(result["total_cents"], 11305)

    def test_vip_gets_two_percent(self):
        result = self.order(customer_id=2)
        self.assertEqual(result["discount_cents"], 19)

    def test_welcome_coupon_not_for_vip(self):
        self.assertEqual(self.order(coupon="WELCOME10")["discount_cents"], 999)
        # characterizes current behavior: for a VIP the coupon is rejected as unknown, not ignored
        with self.assertRaises(service.OrderError):
            self.order(customer_id=2, coupon="WELCOME10")

    def test_unknown_coupon_rejected(self):
        with self.assertRaises(service.OrderError):
            self.order(coupon="NOPE")

    def test_order_is_stored_and_event_published(self):
        result = self.order()
        row = db.get_order(result["id"])
        self.assertEqual(row["status"], "PAID")
        self.assertEqual(row["charge_id"], "ch_test")
        self.publish.assert_called_once_with("order.created", {"order_id": result["id"], "total_cents": 1678})


if __name__ == "__main__":
    unittest.main()
