---
name: Pro feature policy
description: User-approved entitlement requirements for Third Umpire AI and advertised Pro features.
---

Pro users should get unlimited messages with Third Umpire AI. Routes must enforce what the pricing page actually says.

**Why:** The user explicitly requested unlimited Pro messages and consistent advertised versus enforced access.

**How to apply:** Use the existing Pro entitlement, including valid trials and referral rewards, rather than requiring a paid Stripe subscription alone. Do not silently reintroduce a Pro message-count cap.

## Interactive AI request budgets

Budget provider retries and reasoning latency against the web worker's total request deadline, not just the SDK's per-attempt timeout.

**Why:** A production chat request exceeded the 60-second worker deadline despite a 30-second SDK timeout because the provider path retried. The user message had already been committed, leaving the browser's usage counter stale when the worker stopped.

**How to apply:** Keep interactive requests bounded, account for retries explicitly, and refresh server-owned allowances after errors. A killed worker cannot deliver either an application error response or updated usage.
