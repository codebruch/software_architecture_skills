import unittest

from orderdesk.pricing_rules import BulkDiscountStrategy, DiscountStrategyFactory


class BulkDiscountTest(unittest.TestCase):
    def test_no_discount_below_threshold(self):
        self.assertEqual(BulkDiscountStrategy().discount_cents(100_00, 9), 0)

    def test_five_percent_from_ten_items(self):
        self.assertEqual(BulkDiscountStrategy().discount_cents(100_00, 10), 5_00)

    def test_factory_returns_bulk_strategy(self):
        self.assertIsInstance(DiscountStrategyFactory.create(), BulkDiscountStrategy)


if __name__ == "__main__":
    unittest.main()
