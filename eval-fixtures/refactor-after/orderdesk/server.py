import json
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from orderdesk import config, db, reports, service


def validate_order_payload(body):
    items = body.get("items")
    if not isinstance(items, list) or not items:
        return {"items": "must be a non-empty list"}
    return None


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self):
        return self.headers.get("X-Api-Token") == config.API_TOKEN

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        url = urlparse(self.path)
        try:
            if url.path == "/admin/export":
                self._send(200, reports.export_all())
            elif url.path == "/report/top-customers":
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized"})
                self._send(200, reports.top_customers())
            elif url.path == "/orders":
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized"})
                name = parse_qs(url.query).get("customer", [""])[0]
                self._send(200, [dict(o) for o in db.find_orders_by_customer_name(name)])
            elif url.path.startswith("/orders/"):
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized"})
                self._send(200, service.get_order(url.path.split("/")[2]))
            else:
                self._send(404, {"error": "not found"})
        except service.OrderError as e:
            self._send(400, {"error": str(e)})
        except Exception:
            self._send(500, {"error": traceback.format_exc()})

    def do_POST(self):
        url = urlparse(self.path)
        try:
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            body = self._body()
            print("POST", url.path, body)
            if url.path == "/orders":
                errors = validate_order_payload(body)
                if errors:
                    return self._send(400, {"error": "invalid order", "fields": errors})
                self._send(201, service.create_order(body))
            elif url.path.startswith("/orders/") and url.path.endswith("/refund"):
                self._send(200, service.refund_order(url.path.split("/")[2], body["amount_cents"]))
            else:
                self._send(404, {"error": "not found"})
        except service.OrderError as e:
            self._send(400, {"error": str(e)})
        except Exception:
            self._send(500, {"error": traceback.format_exc()})

    def log_message(self, fmt, *args):
        pass


def main():
    db.conn()
    print("orderdesk listening on", config.PORT)
    ThreadingHTTPServer(("0.0.0.0", config.PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
