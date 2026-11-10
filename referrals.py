"""Referral attribution and rewards. All grants are server-owned PostgreSQL transactions."""
import calendar
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import redirect, render_template, session, url_for
from flask_login import current_user
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import db
from models import User, Prediction, ReferralProfile, ReferralIdentity, Referral, ReferralReward, ReferralWelcomeGrant

SG = ZoneInfo("Asia/Singapore")
ATTRIBUTION_DAYS = 30
WELCOME_PRO_DAYS = 30


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def singapore_month(now):
    return now.replace(tzinfo=timezone.utc).astimezone(SG).strftime("%Y-%m")


def add_pro_month(value):
    """A calendar month in Singapore, clipped at the last day of the next month."""
    local = value.replace(tzinfo=timezone.utc).astimezone(SG)
    month = local.month % 12 + 1
    year = local.year + (local.month == 12)
    local = local.replace(year=year, month=month,
                          day=min(local.day, calendar.monthrange(year, month)[1]))
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def canonical_email(value):
    value = (value or "").strip().casefold()
    if "@" not in value:
        return None
    name, domain = value.rsplit("@", 1)
    # Gmail explicitly treats these as one mailbox. Do not guess other providers' rules.
    if domain in ("gmail.com", "googlemail.com"):
        domain = "gmail.com"
        name = name.split("+", 1)[0].replace(".", "")
    return f"{name}@{domain}"


def identity_key(email):
    normalized = canonical_email(email)
    return hashlib.sha256(normalized.encode()).hexdigest() if normalized else None


def ensure_profile(tx, user_id):
    tx.execute(insert(ReferralProfile).values(
        user_id=user_id, code=secrets.token_urlsafe(24), created_at=utc_now()
    ).on_conflict_do_nothing(index_elements=["user_id"]))
    return tx.get(ReferralProfile, user_id)


def register_identity(tx, user, claims, is_new, attribution, known_account=False, now=None):
    """Called inside the authentication transaction, never from submitted form fields."""
    now = now or utc_now()
    ensure_profile(tx, user.id)
    fingerprint = identity_key(user.email)
    duplicate = False
    if fingerprint:
        # Covers pre-programme accounts which have not signed in since launch.
        for other_id, email in tx.execute(select(User.id, User.email).where(User.id != user.id)):
            if identity_key(email) == fingerprint:
                duplicate = True
                break
        tx.execute(insert(ReferralIdentity).values(
            fingerprint=fingerprint, user_id=user.id
        ).on_conflict_do_nothing(index_elements=["fingerprint"]))
        duplicate = duplicate or tx.get(ReferralIdentity, fingerprint).user_id != user.id
    if not is_new or not attribution:
        return
    try:
        code, captured = attribution["code"], float(attribution["captured"])
        valid_time = 0 <= now.replace(tzinfo=timezone.utc).timestamp() - captured <= ATTRIBUTION_DAYS * 86400
    except (KeyError, TypeError, ValueError, OverflowError):
        return
    if not valid_time:
        return
    owner = tx.scalar(select(ReferralProfile).where(ReferralProfile.code == code))
    if not owner or owner.user_id == user.id:
        return
    reason = None
    if duplicate:
        reason = "existing_identity"
    elif known_account:
        reason = "previous_account_on_browser"
    elif not fingerprint or claims.get("email_verified") is not True:
        reason = "verified_email_required"
    referral = Referral(
        referrer_id=owner.user_id, referred_id=user.id, created_at=now,
        status="rejected" if reason else "pending", rejection_reason=reason)
    tx.add(referral)
    if not reason:
        # Friend-side reward: only for referrals that passed every anti-abuse check.
        tx.flush()
        tx.add(ReferralWelcomeGrant(
            referral_id=referral.id, user_id=user.id,
            starts_at=now, expires_at=now + timedelta(days=WELCOME_PRO_DAYS)))


def _award_qualified(tx, referrer, now):
    """Caller holds the referrer's row lock. Unique slots are an additional DB backstop."""
    month = singapore_month(now)
    slots = set(tx.scalars(select(ReferralReward.month_slot).where(
        ReferralReward.referrer_id == referrer.id, ReferralReward.reward_month == month)))
    available = [slot for slot in range(1, 6) if slot not in slots]
    if not available:
        return 0
    pending = tx.scalars(select(Referral).where(
        Referral.referrer_id == referrer.id, Referral.status == "qualified"
    ).order_by(Referral.qualification_at, Referral.id).limit(len(available)).with_for_update()).all()
    earned_until = tx.scalar(select(func.max(ReferralReward.expires_at)).where(
        ReferralReward.referrer_id == referrer.id))
    paid_until = referrer.subscription_period_end if referrer.subscription_active else None
    start = max(filter(None, (now, earned_until, paid_until)))
    for referral, slot in zip(pending, available):
        end = add_pro_month(start)
        tx.add(ReferralReward(
            referral_id=referral.id, referrer_id=referrer.id, reward_month=month,
            month_slot=slot, awarded_at=now, starts_at=start, expires_at=end))
        referral.status = "rewarded"
        start = end
    return len(pending)


def complete_prediction(user_id, prediction_id, engine=None, now=None):
    """Only the successful /predict handler calls this, with its own persisted prediction."""
    now = now or utc_now()
    with Session(engine or db.engine) as tx, tx.begin():
        referral_owner = tx.scalar(select(Referral.referrer_id).where(Referral.referred_id == user_id))
        if not referral_owner:
            return 0
        referrer = tx.scalar(select(User).where(User.id == referral_owner).with_for_update())
        referral = tx.scalar(select(Referral).where(
            Referral.referred_id == user_id).with_for_update())
        if referral.status == "pending":
            prediction = tx.get(Prediction, prediction_id)
            if (prediction is None or prediction.user_id != user_id
                    or prediction.created_at < referral.created_at):
                raise ValueError("Qualification requires a persisted successful prediction")
            referral.status = "qualified"
            referral.prediction_id = prediction_id
            referral.qualification_at = now
            tx.flush()
        return _award_qualified(tx, referrer, now)


def settle_rewards(user_id, engine=None, now=None):
    with Session(engine or db.engine) as tx, tx.begin():
        referrer = tx.scalar(select(User).where(User.id == user_id).with_for_update())
        return _award_qualified(tx, referrer, now or utc_now()) if referrer else 0


def settle_pending_rewards():
    """Hourly sweep; independent workers serialize on each referrer just like /predict."""
    from app import app
    with app.app_context():
        # Recover qualifications after a transient database/service failure following
        # a successful prediction. Anonymous/demo rows have no owner and cannot qualify.
        completed = db.session.execute(select(
            Referral.referred_id, func.min(Prediction.id)
        ).join(Prediction, Prediction.user_id == Referral.referred_id).where(
            Referral.status == "pending", Prediction.created_at >= Referral.created_at
        ).group_by(Referral.referred_id)).all()
        for user_id, prediction_id in completed:
            try:
                complete_prediction(user_id, prediction_id)
            except Exception:
                app.logger.exception("Referral qualification retry failed; attribution retained")
        ids = db.session.scalars(select(Referral.referrer_id).where(
            Referral.status == "qualified").distinct()).all()
        for user_id in ids:
            try:
                settle_rewards(user_id)
            except Exception:
                app.logger.exception("Referral settlement failed; pending rewards retained")


def init_referrals(app, require_login):
    @app.before_request
    def remember_known_account():
        if "prediction_csrf" not in session:
            session["prediction_csrf"] = secrets.token_urlsafe(32)
        if current_user.is_authenticated:
            session["referral_known_account"] = True

    @app.route("/r/<code>")
    def referral_visit(code):
        owner = db.session.scalar(select(ReferralProfile).where(ReferralProfile.code == code))
        if owner and not current_user.is_authenticated and not session.get("referral_known_account"):
            # First attribution wins and survives the OAuth round trip in the signed session.
            prior = session.get("referral_attribution")
            epoch = utc_now().replace(tzinfo=timezone.utc).timestamp()
            if not prior or epoch - prior.get("captured", 0) > ATTRIBUTION_DAYS * 86400:
                session["referral_attribution"] = {"code": code, "captured": epoch}
                session.permanent = True
        return redirect(url_for("index"))

    @app.route("/referrals")
    @require_login
    def referral_dashboard():
        with Session(db.engine) as tx, tx.begin():
            profile = ensure_profile(tx, current_user.id)
            code = profile.code
        settle_rewards(current_user.id)
        month = singapore_month(utc_now())
        successful = db.session.scalar(select(func.count()).select_from(ReferralReward).where(
            ReferralReward.referrer_id == current_user.id, ReferralReward.reward_month == month))
        total = db.session.scalar(select(func.count()).select_from(ReferralReward).where(
            ReferralReward.referrer_id == current_user.id))
        pending = db.session.scalar(select(func.count()).select_from(Referral).where(
            Referral.referrer_id == current_user.id, Referral.status.in_(["pending", "qualified"])))
        history = db.session.scalars(select(Referral).where(
            Referral.referrer_id == current_user.id).order_by(Referral.created_at.desc()).limit(50)).all()
        expiry = current_user.pro_expires_at
        return render_template(
            "referrals.html", referral_link=url_for("referral_visit", code=code, _external=True),
            successful_this_month=successful, pending_referrals=pending,
            total_months_earned=total, pro_until=expiry.replace(tzinfo=timezone.utc).astimezone(SG)
            if expiry and expiry > utc_now() else None, history=history)
