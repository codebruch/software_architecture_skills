---
tags: [sw-architecture]
max_turns: 80
timeout_seconds: 2400
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Review the architecture of this service using the docs in docs/architecture. I can't answer questions today, so take this as my selection up front: whatever else you find, I want to pursue exactly two things - locking down the admin export endpoint, and getting the pricing logic out of create_order so it can be tested. Take it all the way to the plan.
