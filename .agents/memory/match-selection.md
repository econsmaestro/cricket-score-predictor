---
name: Match selection behavior
description: Expected behavior when Predict is selected from a match card.
---

Selecting Predict on a match card should autofill all available details for that specific match, including the correct men's/women's ODI/T20 format. The user should then only need to click Predict.

**Why:** The user explicitly requested this instead of opening a blank form.

**How to apply:** Keep the selected match consistent across format changes and asynchronous loads. If source details are unavailable or the fixture has not started, explain that explicitly rather than inventing live data.
