"""Send one transactional reminder before earned Pro access expires."""
import logging
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import ProExpiryReminder, ReferralReward, ReferralWelcomeGrant, User

logger = logging.getLogger(__name__)

REMINDER_LEAD = timedelta(days=2)
RETRY_DELAY = timedelta(hours=6)
CLAIM_TIMEOUT = timedelta(minutes=15)
SINGAPORE = ZoneInfo("Asia/Singapore")


def _utc_naive(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _eligible_expiry_user(tx, user_id, earned_expiry):
    user = tx.get(User, user_id)
    if user is None or not user.email:
        return None
    # Do not send an earned-access expiry reminder if paid Pro continues later.
    if user.subscription_active:
        if user.subscription_period_end is None:
            return None
        if user.subscription_period_end > earned_expiry:
            return None
    # Legacy Pro grants have no known expiry date.
    if user.is_pro and not user.subscription_status:
        return None
    return user


def _latest_earned_expiry(tx, user_id):
    """Latest end of earned access: referral rewards or the friend-side welcome grant."""
    values = (
        tx.scalar(select(func.max(ReferralReward.expires_at)).where(
            ReferralReward.referrer_id == user_id)),
        tx.scalar(select(func.max(ReferralWelcomeGrant.expires_at)).where(
            ReferralWelcomeGrant.user_id == user_id)),
    )
    return max(filter(None, values), default=None)


def _ensure_due_reminders(engine, now):
    deadline = now + REMINDER_LEAD
    with Session(engine) as tx:
        candidate_ids = set(tx.scalars(select(ReferralReward.referrer_id).distinct()))
        candidate_ids |= set(tx.scalars(select(ReferralWelcomeGrant.user_id)))
        latest_expiries = [(uid, _latest_earned_expiry(tx, uid)) for uid in candidate_ids]

    created = 0
    for user_id, earned_expiry in latest_expiries:
        if earned_expiry is None or not (now < earned_expiry <= deadline):
            continue
        with Session(engine) as check_tx:
            user = _eligible_expiry_user(check_tx, user_id, earned_expiry)
            if user is None:
                continue
        try:
            with Session(engine) as tx, tx.begin():
                tx.add(ProExpiryReminder(
                    user_id=user_id,
                    expires_at=earned_expiry,
                    status="pending",
                    next_attempt_at=now,
                ))
                tx.flush()
            created += 1
        except IntegrityError:
            # The unique user/expiry key makes repeated scheduler runs harmless.
            continue
    return created


def _claim_reminder(engine, reminder_id, now):
    with Session(engine) as tx:
        with tx.begin():
            reminder = tx.scalar(
                select(ProExpiryReminder)
                .where(ProExpiryReminder.id == reminder_id)
                .with_for_update()
            )
            if reminder is None or reminder.status in ("sent", "superseded"):
                return None
            if reminder.next_attempt_at and reminder.next_attempt_at > now:
                return None
            if (
                reminder.status == "sending"
                and reminder.claimed_at
                and reminder.claimed_at > now - CLAIM_TIMEOUT
            ):
                return None

            if reminder.expires_at <= now:
                reminder.status = "superseded"
                return None

            user = _eligible_expiry_user(tx, reminder.user_id, reminder.expires_at)
            latest_expiry = _latest_earned_expiry(tx, reminder.user_id)
            # Rewards may have been extended after this reminder was queued.
            if user is None or latest_expiry != reminder.expires_at:
                reminder.status = "superseded"
                return None

            reminder.status = "sending"
            reminder.claimed_at = now
            reminder.last_attempt_at = now
            reminder.next_attempt_at = None
            reminder.attempt_count += 1
            return user.email, reminder.expires_at


def _build_message(expires_at):
    local_expiry = expires_at.replace(tzinfo=timezone.utc).astimezone(SINGAPORE)
    date_label = local_expiry.strftime("%d %B %Y at %H:%M SGT")
    escaped_date = escape(date_label)
    subject = "Your CricPredict Pro access expires soon"
    plain = (
        "This is a reminder that your earned CricPredict Pro access is scheduled "
        f"to expire on {date_label}. If you have received another reward since "
        "this reminder was scheduled, your access may have been extended. "
        "You can visit CricPredict to review your Pro access. "
        "Questions? Email talldudeplayspiano@gmail.com."
    )
    html = (
        "<div style=\"font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#1f2937\">"
        "<h2 style=\"color:#23456b\">Your CricPredict Pro access expires soon</h2>"
        "<p>This is a reminder that your earned Pro access is scheduled to expire on "
        f"<strong>{escaped_date}</strong>.</p>"
        "<p>If you received another reward after this reminder was scheduled, your "
        "access may have been extended. Visit CricPredict to review your Pro access.</p>"
        "<p>Questions? Email <a href=\"mailto:talldudeplayspiano@gmail.com\">"
        "talldudeplayspiano@gmail.com</a>.</p>"
        "<p style=\"font-size:12px;color:#6b7280\">This is an account-service notice, "
        "not a marketing email.</p></div>"
    )
    return subject, html, plain


def _finish_reminder(engine, reminder_id, now, sent):
    with Session(engine) as tx:
        with tx.begin():
            reminder = tx.scalar(
                select(ProExpiryReminder)
                .where(ProExpiryReminder.id == reminder_id)
                .with_for_update()
            )
            if reminder is None or reminder.status != "sending":
                return
            reminder.claimed_at = None
            if sent:
                reminder.status = "sent"
                reminder.sent_at = now
                reminder.last_error = None
                reminder.next_attempt_at = None
            else:
                reminder.status = "pending"
                reminder.last_error = "Email provider did not confirm delivery."
                reminder.next_attempt_at = now + RETRY_DELAY


def sweep_expiry_reminders(engine, now=None, send_email_func=None):
    """Create and send due reminders; injectable engine/sender make this testable."""
    now = _utc_naive(now)
    if send_email_func is None:
        from gmail_helper import send_email
        send_email_func = send_email

    created = _ensure_due_reminders(engine, now)
    deadline = now + REMINDER_LEAD
    with Session(engine) as tx:
        reminder_ids = tx.scalars(
            select(ProExpiryReminder.id)
            .where(
                ProExpiryReminder.status.in_(("pending", "sending")),
                ProExpiryReminder.expires_at > now,
                ProExpiryReminder.expires_at <= deadline,
                or_(
                    ProExpiryReminder.next_attempt_at.is_(None),
                    ProExpiryReminder.next_attempt_at <= now,
                ),
            )
            .order_by(ProExpiryReminder.expires_at)
            .limit(100)
        ).all()

    sent = failed = 0
    for reminder_id in reminder_ids:
        claim = _claim_reminder(engine, reminder_id, now)
        if claim is None:
            continue
        recipient, expires_at = claim
        subject, html, plain = _build_message(expires_at)
        try:
            delivered = bool(send_email_func(
                recipient, subject, html, plain_body=plain
            ))
        except Exception:
            logger.exception("Pro expiry reminder send failed")
            delivered = False
        _finish_reminder(engine, reminder_id, now, delivered)
        if delivered:
            sent += 1
        else:
            failed += 1

    return {"created": created, "sent": sent, "failed": failed}


def send_pro_expiry_reminders():
    """APScheduler entry point."""
    from app import app, db

    with app.app_context():
        try:
            result = sweep_expiry_reminders(db.engine)
            logger.info(
                "Pro expiry reminder sweep: created=%s sent=%s failed=%s",
                result["created"], result["sent"], result["failed"],
            )
            return result
        except Exception:
            logger.exception("Pro expiry reminder sweep failed")
            return {"created": 0, "sent": 0, "failed": 0}
