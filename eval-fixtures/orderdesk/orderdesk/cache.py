from orderdesk import db

_customers = {}


def customer(customer_id):
    if customer_id not in _customers:
        _customers[customer_id] = db.get_customer(customer_id)
    return _customers[customer_id]
