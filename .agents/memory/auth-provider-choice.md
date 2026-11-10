---
name: Authentication providers
description: User-approved sign-in provider direction for CricPredict.
---

CricPredict should offer Google sign-in alongside the existing Replit sign-in, not replace Replit. Provider identities should map to the same CricPredict user so predictions, Pro access, and referral history remain attached.

**Why:** The user explicitly chose Google alongside Replit and wants Google-related signup without removing the existing option.

**How to apply:** Preserve Replit login and stored user IDs when adding or changing authentication providers; link verified identities safely and never create duplicate accounts solely because the provider changed.

## Google scope compatibility

Request Google's canonical userinfo scope URLs rather than the short `email` and `profile` aliases.

**Why:** Google returns canonical URLs in its token response. The installed OAuthlib rejects the alias-to-URL difference with a scope-change warning after a successful token exchange, before the authenticated-user handler runs.

**How to apply:** Keep requested scopes consistent with Google's returned scope names and retain strict scope validation. Test token-response parsing when changing Google scopes; do not work around mismatches by relaxing scope checks.
