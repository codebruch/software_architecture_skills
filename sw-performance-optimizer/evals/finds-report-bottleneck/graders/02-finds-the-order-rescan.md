---
type: llm
focus: trace
weight: 1
---

The dominant bottleneck is identified as reports.top_customers scanning all orders once per customer (the nested loop, optionally together with the list membership check or the per-customer query), backed by profiler or timing output.
