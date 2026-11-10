from datetime import datetime, timedelta
from typing import Callable

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app import db
from models import (
    ProExpiryReminder,
    Referral,
    ReferralReward,
    User,
)
from pro_expiry_reminders import sweep_expiry_reminders


NOW = datetime(2026, 11, 10, 12, 0, 0)


@pytest.fixture
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.metadata.create_all(test_engine)
    yield test_engine
    db.metadata.drop_all(test_engine)
    test_engine.dispose()


def add_user_with_reward(engine, *, email="member@example.com", expiry=None,
                         subscription_status=None, subscription_period_end=None,
                         is_pro=False, reward_id=1):
    expiry = expiry or NOW + timedelta(days=2)
    with Session(engine) as tx, tx.begin():
        owner = User(
            id=f"owner-{reward_id}",
            email=email,
            subscription_status=subscription_status,
            subscription_period_end=subscription_period_end,
            is_pro=is_pro,
        )
        referred = User(id=f"friend-{reward_id}", email=f"friend{reward_id}@example.com")
        tx.add_all([owner, referred])
        tx.flush()
        referral = Referral(
            referrer_id=owner.id,
            referred_id=referred.id,
            status="rewarded",
            created_at=NOW - timedelta(days=25),
        )
        tx.add(referral)
        tx.flush()
        tx.add(ReferralReward(
            referral_id=referral.id,
            referrer_id=owner.id,
            reward_month="2026-10",
            month_slot=reward_id,
            awarded_at=NOW - timedelta(days=25),
            starts_at=expiry - timedelta(days=30),
            expires_at=expiry,
        ))
    return f"owner-{reward_id}"


def sender_spy(calls, result=True) -> Callable:
    def send_email(to_email, subject, html_body, plain_body=None):
        calls.append({
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "plain": plain_body,
        })
        return result
    return send_email


def test_sends_once_for_earned_expiry_with_singapore_date(engine):
    add_user_with_reward(engine, expiry=NOW + timedelta(hours=72))
    calls = []

    result = sweep_expiry_reminders(engine, NOW, sender_spy(calls))
    assert result == {"created": 1, "sent": 1, "failed": 0}
    assert len(calls) == 1
    assert calls[0]["to"] == "member@example.com"
    assert "expires soon" in calls[0]["subject"].lower()
    assert "13 November 2026 at 20:00 SGT" in calls[0]["plain"]

    second = sweep_expiry_reminders(engine, NOW, sender_spy(calls))
    assert second["sent"] == 0
    assert len(calls) == 1
    with Session(engine) as tx:
        row = tx.query(ProExpiryReminder).one()
        assert row.status == "sent"
        assert row.attempt_count == 1
        assert row.sent_at == NOW


def test_does_not_remind_when_paid_pro_extends_beyond_reward(engine):
    add_user_with_reward(
        engine,
        expiry=NOW + timedelta(days=2),
        subscription_status="active",
        subscription_period_end=NOW + timedelta(days=5),
    )
    calls = []

    result = sweep_expiry_reminders(engine, NOW, sender_spy(calls))
    assert result["sent"] == 0
    assert calls == []
    with Session(engine) as tx:
        assert tx.query(ProExpiryReminder).count() == 0


def test_reminds_when_paid_period_ends_before_earned_access(engine):
    add_user_with_reward(
        engine,
        expiry=NOW + timedelta(days=2),
        subscription_status="active",
        subscription_period_end=NOW + timedelta(days=1),
    )
    calls = []

    result = sweep_expiry_reminders(engine, NOW, sender_spy(calls))
    assert result["sent"] == 1
    assert len(calls) == 1


def test_retries_failed_delivery_after_backoff(engine):
    add_user_with_reward(engine, expiry=NOW + timedelta(days=2))
    calls = []

    first = sweep_expiry_reminders(engine, NOW, sender_spy(calls, result=False))
    assert first["failed"] == 1
    too_soon = sweep_expiry_reminders(
        engine, NOW + timedelta(hours=5), sender_spy(calls)
    )
    assert too_soon["sent"] == 0
    retried = sweep_expiry_reminders(
        engine, NOW + timedelta(hours=6), sender_spy(calls)
    )
    assert retried["sent"] == 1
    assert len(calls) == 2
    with Session(engine) as tx:
        row = tx.query(ProExpiryReminder).one()
        assert row.status == "sent"
        assert row.attempt_count == 2


def test_supersedes_reminder_if_rewards_extend_expiry(engine):
    owner_id = add_user_with_reward(engine, expiry=NOW + timedelta(days=2))
    with Session(engine) as tx, tx.begin():
        old_referral = tx.query(Referral).filter_by(referrer_id=owner_id).one()
        owner = tx.get(User, owner_id)
        referred = User(id="friend-new", email="newfriend@example.com")
        tx.add(referred)
        tx.flush()
        new_referral = Referral(
            referrer_id=owner.id,
            referred_id=referred.id,
            status="rewarded",
            created_at=NOW,
        )
        tx.add(new_referral)
        tx.flush()
        tx.add(ReferralReward(
            referral_id=new_referral.id,
            referrer_id=owner.id,
            reward_month="2026-11",
            month_slot=1,
            awarded_at=NOW,
            starts_at=NOW + timedelta(days=2),
            expires_at=NOW + timedelta(days=32),
        ))
        tx.add(ProExpiryReminder(
            user_id=owner_id,
            expires_at=NOW + timedelta(days=2),
            status="pending",
            next_attempt_at=NOW,
        ))

    calls = []
    result = sweep_expiry_reminders(engine, NOW, sender_spy(calls))
    assert result["sent"] == 0
    assert calls == []
    with Session(engine) as tx:
        row = tx.query(ProExpiryReminder).one()
        assert row.status == "superseded"
