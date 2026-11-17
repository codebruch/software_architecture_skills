from orderdesk import config
from orderdesk.pricing_rules import DiscountStrategyFactory


class PricingError(Exception):
    pass


def compute_totals(items, vip, coupon=None):
    """Pure pricing rules: no database, payment, clock or ids."""
    subtotal = 0
    count = 0
    for item in items:
        if item["qty"] > 0:
            subtotal += item["qty"] * item["unit_cents"]
            count += item["qty"]
    if subtotal == 0:
        raise PricingError("empty order")
    discount = DiscountStrategyFactory.create().discount_cents(subtotal, count)
    if vip:
        if discount > 0:
            discount = discount + (subtotal - discount) * 2 // 100
        else:
            discount = subtotal * 2 // 100
    if coupon:
        if coupon == "WELCOME10" and not vip:
            discount += 10_00
        elif coupon == "FREESHIP":
            pass
        else:
            raise PricingError("unknown coupon")
    if discount > subtotal:
        discount = subtotal
    net = subtotal - discount
    tax = round(net * config.TAX_RATE_PERCENT / 100)
    if net >= config.FREE_SHIPPING_FROM_CENTS or coupon == "FREESHIP":
        shipping = 0
    else:
        shipping = config.SHIPPING_CENTS
    return {"subtotal": subtotal, "discount": discount, "tax": tax, "shipping": shipping,
            "total": net + tax + shipping}
