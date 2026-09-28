"""Stripe integration helpers for Matchday Pro subscriptions.

Environment variables required (set in Replit Secrets):
    STRIPE_SECRET_KEY       sk_live_... or sk_test_...
    STRIPE_PUBLISHABLE_KEY  pk_live_... or pk_test_...
    STRIPE_WEBHOOK_SECRET   whsec_...
    STRIPE_PRICE_ID         price_... (SGD 3.99/month recurring price from Stripe dashboard)

Setup checklist:
1. Create a Stripe account at stripe.com with Singapore as country.
2. In Stripe Dashboard → Products → Add product "Matchday Pro".
3. Add a recurring price: SGD 3.99 / month.
4. Copy the Price ID (price_xxx) into the STRIPE_PRICE_ID secret.
5. In Stripe Dashboard → Developers → Webhooks → Add endpoint:
       https://your-replit-app.replit.app/stripe/webhook
   Select events: customer.subscription.created, customer.subscription.updated,
   customer.subscription.deleted, invoice.payment_succeeded, invoice.payment_failed
6. Copy the webhook signing secret (whsec_xxx) into STRIPE_WEBHOOK_SECRET.
7. Payouts: Stripe Dashboard → Settings → Payouts → Add SGD bank account.
"""

import os
import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def is_configured() -> bool:
    """Return True when all required Stripe env vars are present."""
    return all([stripe.api_key, PRICE_ID, WEBHOOK_SECRET])


def get_or_create_customer(user) -> str:
    """Return the Stripe customer ID for a user, creating one if needed.

    Args:
        user: SQLAlchemy User instance with .email, .display_name, .id fields.

    Returns:
        Stripe customer ID string (cus_xxx).
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email or "",
        name=user.display_name,
        metadata={"replit_user_id": user.id},
    )

    from app import db
    user.stripe_customer_id = customer.id
    db.session.commit()

    return customer.id


def create_checkout_session(user, success_url: str, cancel_url: str) -> stripe.checkout.Session:
    """Create a Stripe Checkout session for the Matchday Pro monthly plan.

    Args:
        user: Authenticated User model instance.
        success_url: URL to redirect after successful payment (include ?session_id={CHECKOUT_SESSION_ID}).
        cancel_url: URL to redirect when user cancels.

    Returns:
        stripe.checkout.Session object — use .url to redirect the user.
    """
    customer_id = get_or_create_customer(user)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": PRICE_ID, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"replit_user_id": user.id},
        subscription_data={
            "metadata": {"replit_user_id": user.id},
            "trial_period_days": 7,   # 7-day free trial to reduce friction
        },
        allow_promotion_codes=True,
    )
    return session


def create_portal_session(customer_id: str, return_url: str) -> stripe.billing_portal.Session:
    """Create a Stripe Customer Portal session so users can manage/cancel.

    Args:
        customer_id: Stripe cus_xxx ID.
        return_url: URL to redirect after the portal session.

    Returns:
        stripe.billing_portal.Session — use .url to redirect.
    """
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )


def handle_webhook(payload: bytes, sig_header: str):
    """Verify and parse a Stripe webhook payload.

    Args:
        payload: Raw request body bytes (must not be parsed first).
        sig_header: Value of the Stripe-Signature HTTP header.

    Returns:
        stripe.Event on success.

    Raises:
        stripe.error.SignatureVerificationError on bad signature.
        ValueError on missing webhook secret.
    """
    if not WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

    return stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)


def sync_subscription_to_user(user, subscription):
    """Update User model fields from a Stripe Subscription object.

    Call this from the webhook handler whenever a subscription event arrives.

    Args:
        user: SQLAlchemy User instance.
        subscription: stripe.Subscription object.
    """
    from app import db
    from datetime import datetime

    user.stripe_subscription_id = subscription.id
    user.subscription_status = subscription.status
    user.is_pro = subscription.status in ("active", "trialing")

    period_end = getattr(subscription, "current_period_end", None)
    if period_end:
        user.subscription_period_end = datetime.utcfromtimestamp(period_end)

    db.session.commit()
