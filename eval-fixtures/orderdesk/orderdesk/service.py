import uuid
from datetime import datetime

from orderdesk import cache, config, db, events, payments
from orderdesk.pricing_rules import DiscountStrategyFactory


class OrderError(Exception):
    pass


def create_order(payload):
    customer = cache.customer(payload["customer_id"])
    if customer is None:
        raise OrderError("unknown customer")
    items = payload["items"]
    subtotal = 0
    count = 0
    for item in items:
        if item["qty"] > 0:
            subtotal += item["qty"] * item["unit_cents"]
            count += item["qty"]
    if subtotal == 0:
        raise OrderError("empty order")
    discount = DiscountStrategyFactory.create().discount_cents(subtotal, count)
    if customer["vip"]:
        if discount > 0:
            discount = discount + (subtotal - discount) * 2 // 100
        else:
            discount = subtotal * 2 // 100
    coupon = payload.get("coupon")
    if coupon:
        if coupon == "WELCOME10" and not customer["vip"]:
            discount += 10_00
        elif coupon == "FREESHIP":
            pass
        else:
            raise OrderError("unknown coupon")
    if discount > subtotal:
        discount = subtotal
    net = subtotal - discount
    tax = int(net * config.TAX_RATE_PERCENT / 100)
    if net >= config.FREE_SHIPPING_FROM_CENTS or coupon == "FREESHIP":
        shipping = 0
    else:
        shipping = config.SHIPPING_CENTS
    total = net + tax + shipping
    order_id = str(uuid.uuid4())
    charge_id = payments.charge(payload["card_number"], total, order_id)
    now = datetime.now().isoformat()
    c = db.conn()
    c.execute(
        "INSERT INTO orders (id, customer_id, status, subtotal_cents, discount_cents, tax_cents,"
        " shipping_cents, total_cents, charge_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (order_id, customer["id"], "PAID", subtotal, discount, tax, shipping, total, charge_id, now),
    )
    for item in items:
        if item["qty"] > 0:
            c.execute(
                "INSERT INTO order_items (order_id, sku, qty, unit_cents) VALUES (?,?,?,?)",
                (order_id, item["sku"], item["qty"], item["unit_cents"]),
            )
    c.commit()
    events.publish("order.created", {"order_id": order_id, "total_cents": total})
    return {"id": order_id, "status": "PAID", "total_cents": total, "tax_cents": tax,
            "discount_cents": discount, "shipping_cents": shipping}


def refund_order(order_id, amount_cents):
    order = db.get_order(order_id)
    if order is None:
        raise OrderError("unknown order")
    remaining = order["total_cents"] - order["refunded_cents"]
    if amount_cents > remaining:
        raise OrderError("refund exceeds remaining amount")
    payments.refund(order["charge_id"], amount_cents)
    refunded = order["refunded_cents"] + amount_cents
    status = "REFUNDED" if refunded == order["total_cents"] else "OPEN"
    c = db.conn()
    c.execute("UPDATE orders SET refunded_cents = ?, status = ? WHERE id = ?", (refunded, status, order_id))
    c.commit()
    events.publish("order.refunded", {"order_id": order_id, "amount_cents": amount_cents})
    return {"id": order_id, "status": status, "refunded_cents": refunded}


def get_order(order_id):
    order = db.get_order(order_id)
    if order is None:
        raise OrderError("unknown order")
    return dict(order)
