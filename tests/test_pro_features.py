"""Real route/entitlement tests in isolated PostgreSQL schemas; no external AI calls."""
from datetime import datetime, timedelta
from uuid import uuid4
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import text

from app import app, db
from models import (
    User, SupportChat, Referral, ReferralReward, ReferralWelcomeGrant,
)
from chat_access import chat_allowance
import routes
import email_responder


@pytest.fixture
def feature_db():
    with app.app_context():
        original = db.engine
        schema = "pro_features_" + uuid4().hex
        with original.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = original.execution_options(schema_translate_map={None: schema})
        db.engines[None] = engine
        db.metadata.create_all(engine)
        try:
            yield
        finally:
            db.session.remove()
            db.engines[None] = original
            with original.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def sign_in(client, tier="free"):
    now = datetime.utcnow()
    user = User(id="feature-user", email="feature@example.test")
    if tier in ("paid", "trial", "expired_paid"):
        user.subscription_status = "trialing" if tier == "trial" else "active"
        user.subscription_period_end = now + timedelta(
            days=-1 if tier == "expired_paid" else 5,
        )
    db.session.add(user)
    if tier in ("earned", "welcome", "expired_earned"):
        other = User(id="other", email="other@example.test")
        db.session.add(other)
        db.session.flush()
        referral = Referral(
            referrer_id=user.id if tier != "welcome" else other.id,
            referred_id=other.id if tier != "welcome" else user.id,
            status="rewarded",
        )
        db.session.add(referral)
        db.session.flush()
        expiry = now + timedelta(days=-1 if tier == "expired_earned" else 5)
        if tier == "welcome":
            db.session.add(ReferralWelcomeGrant(
                referral_id=referral.id, user_id=user.id,
                starts_at=now - timedelta(days=25), expires_at=expiry,
            ))
        else:
            db.session.add(ReferralReward(
                referral_id=referral.id, referrer_id=user.id,
                reward_month=now.strftime("%Y-%m"), month_slot=1,
                awarded_at=now - timedelta(days=5),
                starts_at=now - timedelta(days=5), expires_at=expiry,
            ))
    db.session.commit()
    with client.session_transaction() as stored:
        stored["_user_id"] = user.id
        stored["_fresh"] = True
        stored["auth_provider"] = "google"
        stored["chat_csrf"] = "synthetic-csrf"
        stored["chat_session_id"] = "feature-chat"
    return user


def seed_messages(user, count, days_ago=0):
    db.session.add_all([
        SupportChat(
            session_id="old-chat", user_id=user.id, role="user",
            message="Previous question", created_at=datetime.utcnow() - timedelta(days=days_ago),
        ) for _ in range(count)
    ])
    db.session.commit()


@pytest.mark.parametrize("tier", ["paid", "trial", "earned", "welcome"])
def test_all_pro_entitlements_get_unlimited_chat_and_full_report(
    feature_db, client, monkeypatch, tier,
):
    user = sign_in(client, tier)
    seed_messages(user, 51)
    replies = []
    monkeypatch.setattr(
        email_responder, "generate_chat_reply",
        lambda history, **kwargs: replies.append(history) or "Synthetic AI reply",
    )
    page = client.get("/support-chat")
    assert page.status_code == 200
    assert b"Unlimited messages" in page.data
    assert b"let remaining = null;" in page.data
    assert b"let unlimited = true;" in page.data
    assert b'id="quotaExceeded"' not in page.data
    script = next(
        script for script in re.findall(r"<script>(.*?)</script>", page.text, re.S)
        if "const CSRF" in script
    )
    parsed = subprocess.run(
        ["node", "--check"], input=script, text=True,
        capture_output=True, timeout=10,
    )
    assert parsed.returncode == 0, parsed.stderr
    response = client.post("/api/support-chat", json={
        "message": "A cricket question", "csrf_token": "synthetic-csrf",
    })
    assert response.status_code == 200
    assert response.json["unlimited"] is True
    assert response.json["remaining"] is None
    assert response.json["weekly_limit"] is None
    assert response.json["renews_at"] is None
    assert len(replies) == 1
    report = client.post("/prematch", data={
        "venue": routes.ALL_VENUES[0], "match_format": "mens_odi",
    })
    assert report.status_code == 200
    assert b"Toss Strategy:" in report.data
    assert b"Explore Matchday Pro" not in report.data


@pytest.mark.parametrize("tier", ["free", "expired_paid", "expired_earned"])
def test_free_and_expired_users_keep_basic_summary_and_free_quota(
    feature_db, client, monkeypatch, tier,
):
    user = sign_in(client, tier)
    seed_messages(user, 50)
    monkeypatch.setattr(
        email_responder, "generate_chat_reply",
        lambda *args, **kwargs: pytest.fail("AI called for an exhausted Free account"),
    )
    monkeypatch.setattr(
        routes, "build_prematch_analysis",
        lambda *args, **kwargs: pytest.fail("Premium report built for non-Pro user"),
    )
    page = client.get("/support-chat")
    assert b"0 of 50 messages" in page.data
    assert b'id="quotaExceeded"' in page.data
    response = client.post("/api/support-chat", json={
        "message": "Question", "csrf_token": "synthetic-csrf", "unlimited": True,
    })
    assert response.status_code == 429
    assert response.json["unlimited"] is False
    assert response.json["remaining"] == 0
    # A user-supplied flag cannot unlock the full report.
    summary = client.post("/prematch", data={
        "venue": routes.ALL_VENUES[0], "match_format": "mens_odi",
        "has_pro": "true", "full_report": "true",
    })
    assert summary.status_code == 200
    assert b"Basic pre-match summary" in summary.data
    assert b"Explore Matchday Pro" in summary.data
    assert b"Toss Strategy:" not in summary.data
    assert b"data-target-width=" not in summary.data


def test_free_message_50_allowed_51_blocked_and_new_chat_cannot_reset(
    feature_db, client, monkeypatch,
):
    user = sign_in(client)
    seed_messages(user, 49)
    monkeypatch.setattr(email_responder, "generate_chat_reply", lambda *a, **kw: "Reply")
    payload = {"message": "Last free question", "csrf_token": "synthetic-csrf"}
    response = client.post("/api/support-chat", json=payload)
    assert response.status_code == 200
    assert response.json["remaining"] == 0
    assert response.json["unlimited"] is False
    assert response.json["renews_at"]
    assert client.post("/api/support-chat/clear", json=payload).status_code == 200
    assert client.post("/api/support-chat", json=payload).status_code == 429


def test_old_messages_age_out_of_free_quota(feature_db, client):
    user = sign_in(client)
    seed_messages(user, 50, days_ago=8)
    assert chat_allowance(user)["remaining"] == 50


def test_expiry_is_enforced_even_on_previously_unlimited_page(feature_db, client, monkeypatch):
    user = sign_in(client, "paid")
    seed_messages(user, 50)
    assert b"Unlimited messages" in client.get("/support-chat").data
    user.subscription_period_end = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    monkeypatch.setattr(
        email_responder, "generate_chat_reply",
        lambda *a, **kw: pytest.fail("Expired Pro must not bypass the Free cap"),
    )
    response = client.post("/api/support-chat", json={
        "message": "Question", "csrf_token": "synthetic-csrf",
    })
    assert response.status_code == 429
    assert response.json["unlimited"] is False
    assert response.json["weekly_limit"] == 50


def test_concurrent_free_requests_cannot_exceed_allowance(feature_db, client, monkeypatch):
    user = sign_in(client)
    seed_messages(user, 49)
    monkeypatch.setattr(email_responder, "generate_chat_reply", lambda *a, **kw: "Reply")
    barrier = Barrier(2)

    def send_question(index):
        with app.test_client() as concurrent_client:
            with concurrent_client.session_transaction() as stored:
                stored["_user_id"] = "feature-user"
                stored["_fresh"] = True
                stored["chat_csrf"] = "synthetic-csrf"
                stored["chat_session_id"] = f"concurrent-{index}"
            barrier.wait(timeout=10)
            return concurrent_client.post("/api/support-chat", json={
                "message": "Question", "csrf_token": "synthetic-csrf",
            }).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        statuses = list(workers.map(send_question, [1, 2]))
    assert sorted(statuses) == [200, 429]
    assert SupportChat.query.filter_by(user_id=user.id, role="user").count() == 50


def test_anonymous_gets_basic_only_and_cannot_use_chat(feature_db, client, monkeypatch):
    monkeypatch.setattr(
        routes, "build_prematch_analysis",
        lambda *a, **kw: pytest.fail("Anonymous premium report"),
    )
    response = client.post("/prematch", data={
        "venue": routes.ALL_VENUES[0], "match_format": "womens_t20",
    })
    assert response.status_code == 200
    assert b"Explore Matchday Pro" in response.data
    assert client.post("/api/support-chat", json={"message": "Hello"}).status_code == 401


def test_unlimited_chat_still_requires_csrf_and_message_size(feature_db, client, monkeypatch):
    sign_in(client, "paid")
    monkeypatch.setattr(
        email_responder, "generate_chat_reply",
        lambda *a, **kw: pytest.fail("AI should not be called"),
    )
    assert client.post("/api/support-chat", json={"message": "Hello"}).status_code == 403
    assert client.post("/api/support-chat", json={
        "message": "x" * 1001, "csrf_token": "synthetic-csrf",
    }).status_code == 400


@pytest.mark.parametrize("tier,allowed", [("free", False), ("paid", True), ("expired_paid", False)])
def test_saved_prediction_and_alert_routes_enforce_pro(feature_db, client, tier, allowed):
    sign_in(client, tier)
    requests = [
        ("GET", "/pro/predictions", {}),
        ("POST", "/pro/predictions/save", {"json": {"venue": "Test", "predicted_score": 180}}),
        ("GET", "/pro/alerts", {}),
        ("POST", "/pro/alerts", {"data": {"alert_email": "feature@example.test"}}),
    ]
    for method, path, kwargs in requests:
        response = client.open(path, method=method, **kwargs)
        if not allowed:
            assert response.status_code == 302
            assert response.location.endswith("/pricing")
        elif path == "/pro/alerts" and method == "POST":
            assert response.status_code == 302
            assert response.location.endswith("/pro/alerts")
        else:
            assert response.status_code == 200
    if allowed:
        saved_id = db.session.query(routes.SavedPrediction).one().id
        alert_id = db.session.query(routes.MatchAlert).one().id
    else:
        saved_id = alert_id = 99999
    for path, kwargs in [
        (f"/pro/predictions/{saved_id}/actual", {"json": {"actual_score": 175}}),
        (f"/pro/alerts/{alert_id}/delete", {}),
    ]:
        response = client.post(path, **kwargs)
        if not allowed:
            assert response.status_code == 302
            assert response.location.endswith("/pricing")
        else:
            assert response.status_code == (200 if "/actual" in path else 302)
