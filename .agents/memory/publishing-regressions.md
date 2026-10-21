---
name: Publishing regression checks
description: Repeated publish failures can reflect restored source rather than an ineffective startup fix.
---

When a previously fixed startup crash reappears, verify the current source and build history before diagnosing a new cause or telling the user merely to retry.

**Why:** A successful publish was followed by a new failure with the same SQLAlchemy reserved-attribute error; both the earlier source correction and its regression test were absent in the current workspace. The reason those files were restored was not established.

**How to apply:** Compare the latest failure, current source and intervening successful builds. Repair the current files and restore the regression guard; do not assume a prior session's edits persisted, and do not speculate about who restored them.
