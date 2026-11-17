import json
import urllib.request

PAYFAST_URL = "https://api.payfast.example/v1"
PAYFAST_API_KEY = "pf_live_9f3c2a7b41d8e6a05c1b"


class PaymentError(Exception):
    pass


def _post(path, body):
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                PAYFAST_URL + path,
                data=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + PAYFAST_API_KEY, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except Exception as e:
            last_error = e
    raise PaymentError(str(last_error))


def charge(card_number, amount_cents, reference):
    print("charging card", card_number, "amount", amount_cents)
    return _post("/charges", {"card": card_number, "amount": amount_cents, "reference": reference})["id"]


def refund(charge_id, amount_cents):
    return _post("/refunds", {"charge": charge_id, "amount": amount_cents})["id"]
