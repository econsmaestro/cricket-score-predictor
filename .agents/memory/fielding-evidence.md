---
name: Fielding rating evidence
description: User requirement for defensible fielding ratings in CricPredict.
---

Fielding ratings used in this app must be justifiable.

**Why:** The user said, "I just think that fielding ratings used should be something we can justify," after learning the displayed percentages were manually assigned rather than measured.

**How to apply:** Do not justify arbitrary team values as observed statistics. Any proposed replacement should explain its evidence, calculation and limitations.

Keep the existing prediction engine as the baseline and new fielding work in shadow mode until the user approves a replacement. Do not deploy or publish it automatically.

**Why:** The user explicitly approved modular implementation with this restriction, and said existing hardcoded ratings must not be removed before replacements are validated.

**How to apply:** Compare identical historical observations, disclose regressions and underidentified components, and never claim improvement from unchanged shadow outputs.

Historical ratings must use only information available before prediction. Catching, ground fielding and throwing need separate confidence indicators; no overall FQR is allowed when evidence is insufficient.

**Why:** The user explicitly required these safeguards and said catches taken cannot directly measure catching ability without opportunities.

**How to apply:** Preserve missing denominators as unavailable. Pressure analysis must control for match situation, wickets lost, over number and required run rate; association is not causation.
