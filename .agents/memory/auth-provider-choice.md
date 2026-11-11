---
name: Authentication providers
description: User-approved sign-in provider direction for CricPredict.
---

CricPredict should offer Google sign-in alongside the existing Replit sign-in, not replace Replit. Provider identities should map to the same CricPredict user so predictions, Pro access, and referral history remain attached.

**Why:** The user explicitly chose Google alongside Replit and wants Google-related signup without removing the existing option.

**How to apply:** Preserve Replit login and stored user IDs when adding or changing authentication providers; link verified identities safely and never create duplicate accounts solely because the provider changed.

## Google scope compatibility

Request Google's canonical userinfo scope URLs rather than the short `email` and `profile` aliases.

**Why:** Google returns canonical URLs in its token response. The installed OAuthlib rejects the alias-to-URL difference with a scope-change warning after a successful token exchange, before the authenticated-user handler runs. The user confirmed that Google sign-in works after switching to canonical scopes.

**How to apply:** Keep requested scopes consistent with Google's returned scope names and retain strict scope validation. Test token-response parsing when changing Google scopes; do not work around mismatches by relaxing scope checks.

## Independent provider sessions

An authenticated Google session must not depend on any retained Replit OAuth credentials.

**Why:** Accounts can use both providers, so a stale credential from a previous Replit login must not invalidate a later successful Google login. Expired Replit sessions also exposed an interaction between the login guard and the authenticated sign-in redirect.

**How to apply:** Exercise protected-page navigation with mixed-provider and expired sessions, not just successful OAuth callbacks. Failed reauthentication must reach a usable sign-in page without cycling back to the protected destination.
