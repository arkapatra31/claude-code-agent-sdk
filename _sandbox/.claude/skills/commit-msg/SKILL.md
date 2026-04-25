---
name: commit-msg
description: Convert a freeform change description into a Conventional Commits subject + body.
---

When invoked, follow this recipe:

1. Identify the change type: feat | fix | chore | refactor | docs | test.
2. Write a single subject line: `<type>(<scope>): <imperative summary>`
   - <= 72 chars, lowercase, no trailing period.
3. Add a 1-3 line body explaining the *why*, not the *what*.
4. Output ONLY the commit message — no preamble, no fences.
