from abc import ABC, abstractmethod

from orderdesk import config


class DiscountStrategy(ABC):
    @abstractmethod
    def discount_cents(self, subtotal_cents, item_count):
        ...


class BulkDiscountStrategy(DiscountStrategy):
    def discount_cents(self, subtotal_cents, item_count):
        if item_count >= config.BULK_DISCOUNT_THRESHOLD:
            return subtotal_cents * config.BULK_DISCOUNT_PERCENT // 100
        return 0


class DiscountStrategyFactory:
    @staticmethod
    def create(kind="bulk"):
        return BulkDiscountStrategy()
