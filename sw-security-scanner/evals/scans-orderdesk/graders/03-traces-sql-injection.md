---
type: llm
focus: trace
weight: 1
---

The scan reports SQL injection in find_orders_by_customer_name in orderdesk/db.py, and traces it from the customer query parameter of GET /orders to the string-built query.
