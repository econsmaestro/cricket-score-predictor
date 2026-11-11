---
name: Referral programme policy
description: Referral eligibility, calendar months, queued rewards and identity assurance limits.
---

Registered users earn one Pro calendar month per genuinely new referred account
after its first successful non-demo prediction. At most five rewards are awarded
per Singapore calendar month, with no lifetime limit. Extra qualified referrals
remain queued for later months rather than being discarded.

**Why:** The user requested the five-per-month programme and stacking expiry,
and the implementation approach explicitly retained over-cap referrals.

**How to apply:** Keep monthly counting in Singapore time. Calendar-month
extensions clip at month-end and extend the resulting expiry. Referral grants
extend existing Pro access; they do not change recurring Stripe billing.

Identity assurance must be described honestly: known accounts, canonical verified
email identities and previously authenticated browsers are screened, not shared
IP addresses. A different identity on a different device cannot reliably be
identified as the same human using this authentication system.

**Why:** The user requires anti-abuse safeguards without rejecting shared-IP
users. Complete human deduplication is not supported by the existing identity
provider; this limitation was disclosed before implementation.

**How to apply:** Do not claim this is proof of distinct people or promise
complete multi-account fraud prevention. Preserve provider-side verification and
do not replace it with posted flags or IP-only rules.

Notify the referrer when a reward is actually awarded, rather than merely when
a friend registers or becomes qualified beyond the monthly cap.

**Why:** The user requested a completion notification by email or popup; an
in-app notice avoids introducing email delivery dependencies.

**How to apply:** Keep notifications tied to committed rewards. A queued
qualification must not be described as an awarded month.
