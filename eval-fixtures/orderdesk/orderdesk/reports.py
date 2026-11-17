from orderdesk import config, db


def format_report_row(rank, customer, total_cents, order_count):
    name = customer["name"]
    if len(name) > 24:
        name = name[:21] + "..."
    if customer["vip"] and total_cents > 1000_00:
        tier = "platinum"
    elif customer["vip"]:
        tier = "gold"
    elif total_cents > 1000_00:
        tier = "silver"
    elif total_cents > 100_00:
        tier = "bronze"
    else:
        tier = "none"
    if order_count == 0:
        avg = 0
    elif order_count == 1:
        avg = total_cents
    else:
        avg = total_cents // order_count
    email = customer["email"] or ""
    if "@" in email:
        user, domain = email.split("@", 1)
        email = user[:2] + "***@" + domain
    return {"rank": rank, "name": name, "tier": tier, "total_cents": total_cents,
            "orders": order_count, "avg_cents": avg, "email": email}


def top_customers():
    orders = db.all_orders()
    seen = []
    for order in orders:
        if order["customer_id"] not in seen:
            seen.append(order["customer_id"])
    totals = []
    for customer_id in seen:
        total = 0
        count = 0
        for order in orders:
            if order["customer_id"] == customer_id and order["status"] != "REFUNDED":
                total += order["total_cents"] - order["refunded_cents"]
                count += 1
        customer = db.get_customer(customer_id)
        totals.append((total, count, customer))
    totals.sort(key=lambda t: t[0], reverse=True)
    rows = []
    for rank, (total, count, customer) in enumerate(totals[: config.MAX_REPORT_ROWS], start=1):
        rows.append(format_report_row(rank, customer, total, count))
    return rows


def export_all():
    out = []
    for customer in db.all_customers():
        out.append({"id": customer["id"], "name": customer["name"], "email": customer["email"],
                    "orders": [dict(o) for o in db.find_orders_by_customer_name(customer["name"])]})
    return out
