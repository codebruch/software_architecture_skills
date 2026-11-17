---
type: llm
focus: trace
weight: 1
---

A sequence diagram for creating an order shows the PayFast charge happening before the order is inserted into the database, followed by the order.created event being published.
