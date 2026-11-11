# Referral programme schema

## Referral reward notifications

Adds `referral_reward_notice`, with `reward_id` as its primary key and foreign
key to `referral_reward.id`, plus a non-null `shown_at` timestamp. The existing
development schema setup creates this new table. Include it in the Publish
schema-diff review; no existing records need to be changed or deleted.

The next rendered page for the referrer shows previously unannounced rewards,
including rewards earned before this feature was added. The receipt prevents
repeat notifications across visits and devices. This is an in-app notification,
not an email or a real-time push notification.

The SQLAlchemy models remain the schema source of truth. This change adds
`referral_profile`, `referral_identity`, `referral`, `referral_reward`, plus nullable
`prediction.user_id` (foreign key to `users.id`, indexed). Existing prediction rows
remain anonymous and do not qualify for rewards. No users or subscription records
are deleted or replaced.

Development: create the four new tables using the existing SQLAlchemy development
setup. Apply this additive change to the existing prediction table in development:

```sql
ALTER TABLE prediction ADD COLUMN IF NOT EXISTS user_id VARCHAR REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_prediction_user_id ON prediction(user_id);
```

Production: use Replit's Publish schema-diff review to apply the development schema.
Do not run this SQL against production, add it to a deployment hook, or introduce
startup-time `ALTER TABLE` statements. Preserve production data in the Publish UI.

Existing users get a referral code on their next sign-in or dashboard visit.
Their existing identities are checked during new registrations even before they
have visited the programme. No production data backfill is required.

## Programme decisions

- Qualification requires a server-generated, saved, non-demo prediction owned by
  the newly registered account. There is no public reward-grant endpoint.
- Attribution is first-touch, expires after 30 days, and survives OAuth in the
  Flask-signed session.
- Identity eligibility requires `email_verified: true` from the authentication
  provider's authenticated UserInfo response. Replit's public OIDC discovery
  advertises this claim. Missing verification fails closed; the provider must
  supply that claim for referrals to qualify. No request parameter can substitute
  for it. The UserInfo subject must match the OAuth ID token's subject.
- Known accounts, canonical email aliases (including Gmail dot/plus aliases),
  and browsers already associated with an account cannot earn another referral.
  IP addresses are not used. Different identities/devices cannot reliably be
  linked to one human with the current authentication system.
- Qualified referrals beyond five awards in a Singapore calendar month are queued.
  The existing scheduler processes them hourly, and dashboard visits also settle
  them. No referral is lost at the monthly boundary.
- The hourly sweep also recovers saved prediction qualifications if immediate
  reward processing encountered a transient error.
- Pro authorization uses `User.has_pro`, combining existing paid/manual
  entitlements with earned expiry history. Stripe remains the paid subscription
  authority; rewards do not modify Stripe billing, payment dates or charges.
- A month is a Singapore calendar month, clipping dates at month-end. Successive
  grants extend the resulting expiry (January 31 -> February 28 -> March 28).
