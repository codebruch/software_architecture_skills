---
tags: [sw-architecture]
max_turns: 80
timeout_seconds: 2400
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

GET /report/top-customers has got slow - about a second per call now that we have roughly 2,000 customers and 20,000 orders (python3 scripts/seed.py 2000 20000 gives you data of that shape). I need it under 100 ms. Docs are in docs/architecture. What should we do?
