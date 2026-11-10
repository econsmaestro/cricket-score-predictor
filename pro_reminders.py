"""Email reminders sent REMINDER_DAYS before earned (referral) Pro access runs out."""
import logging
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db
from models import User, ReferralReward, ReferralWelcomeGrant, ProExpiryReminder

logger = logging.getLogger(__name__)
REMINDER_DAYS = 2
SG = ZoneInfo("Asia/Singapore")


def _base_url():
    domain = (os.environ.get("REPLIT_DOMAINS") or "").split(",")[0].strip()
    return os.environ.get("APP_BASE_URL") or (f"https://{domain}" if domain else "")


def _default_send(to_email, subject, html, text):
    from gmail_helper import send_email
    return send_email(to_email, subject, html, text)


def build_message(user, expires_at):
    ends = expires_at.replace(tzinfo=timezone.utc).astimezone(SG).strftime("%-d %b %Y, %-I:%M %p SGT")
    base = _base_url()
    name = user.display_name
    subject = "Your Matchday Pro access ends in 2 days"
    text = (f"Hi {name},\n\nYour Matchday Pro access ends on {ends}. After that you'll go back to "
            f"the free plan (no full pre-match reports, saved predictions or match alerts).\n\n"
            f"Keep Pro for SGD 3.99/mo: {base}/pricing\n"
            f"Or earn more free time by referring friends: {base}/referrals\n")
    html = (f"<p>Hi {name},</p><p>Your <strong>Matchday Pro</strong> access ends on "
            f"<strong>{ends}</strong>. After that you'll go back to the free plan (no full pre-match "
            f"reports, saved predictions or match alerts).</p>"
            f"<p><a href=\"{base}/pricing\">Keep Pro for SGD 3.99/mo</a> &middot; "
            f"<a href=\"{base}/referrals\">Earn more free time by referring friends</a></p>")
    return subject, html, text


def send_pro_expiry_reminders(engine=None, now=None, send=None):
    """Remind users whose Pro (referral rewards / welcome grant) ends within 2 days.

    Users with a live Stripe subscription are skipped: their access renews, so there is
    nothing running out. Each distinct expiry is reminded at most once.
    Returns the number of reminders sent.
    """
    now = now or datetime.utcnow()
    send = send or _default_send
    horizon = now + timedelta(days=REMINDER_DAYS)
    sent = 0
    with Session(engine or db.engine) as tx:
        ids = set(tx.scalars(select(ReferralReward.referrer_id).where(
            ReferralReward.expires_at > now)))
        ids |= set(tx.scalars(select(ReferralWelcomeGrant.user_id).where(
            ReferralWelcomeGrant.expires_at > now)))
        for user_id in ids:
            user = tx.get(User, user_id)
            if not user or not user.email or user.subscription_active:
                continue
            expiry = user.pro_expires_at
            if expiry is None or not (now < expiry <= horizon):
                continue
            try:
                with tx.begin_nested():
                    tx.add(ProExpiryReminder(user_id=user_id, expires_at=expiry, sent_at=now))
                    tx.flush()
            except IntegrityError:
                continue  # already reminded for this expiry (or another worker is)
            tx.commit()
            try:
                ok = send(user.email, *build_message(user, expiry))
            except Exception:
                logger.exception("Pro expiry reminder failed for %s", user_id)
                ok = False
            if ok:
                sent += 1
            else:  # release the claim so the next hourly run retries
                tx.execute(ProExpiryReminder.__table__.delete().where(
                    ProExpiryReminder.user_id == user_id, ProExpiryReminder.expires_at == expiry))
                tx.commit()
    return sent


def run_scheduled():
    """Scheduler entry point (needs an app context for db.engine)."""
    from app import app
    with app.app_context():
        send_pro_expiry_reminders()
