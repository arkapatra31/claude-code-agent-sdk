---
name: pr-description
description: Use when the user has a diff and wants a GitHub PR description in our team's standard format.
---

Output exactly these sections, in order, as Markdown:

## Summary
- 1-3 bullets, each <= 20 words. Focus on user-visible change.

## Why
- One short paragraph explaining the motivation.

## Test plan
- Bulleted checklist of how a reviewer can verify.

Rules:
  - Do not include a "Changes" section that lists every file.
  - Never invent test results — describe what to RUN, not what passed.
  - If the diff is empty, reply: "No changes detected."
