import unittest

from orderdesk import pricing


class ComputeTotalsTest(unittest.TestCase):
    def test_free_shipping_from_fifty(self):
        totals = pricing.compute_totals([{"sku": "a", "qty": 1, "unit_cents": 5000}], vip=False)
        self.assertEqual(totals["shipping"], 0)

    def test_empty_order_rejected(self):
        with self.assertRaises(pricing.PricingError):
            pricing.compute_totals([], vip=False)


if __name__ == "__main__":
    unittest.main()
