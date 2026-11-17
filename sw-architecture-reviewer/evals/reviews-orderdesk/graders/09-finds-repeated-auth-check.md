---
type: llm
focus: trace
weight: 1
---

The review notes that the API token check is repeated inside each route branch instead of being enforced in one place, and connects this to /admin/export having been left without it.
