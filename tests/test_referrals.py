"""Real PostgreSQL transactions in a disposable schema, not production or app data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import app, db
from models import User, Prediction, Referral, ReferralProfile, ReferralReward, ReferralWelcomeGrant
from referrals import (
    add_pro_month, singapore_month, canonical_email, ensure_profile,
    register_identity, complete_prediction, settle_rewards,
)

NOW = datetime(2026, 11, 4, 6)


@pytest.fixture
def referral_db():
    """Separate schema per test; exercise the same row locks and constraints as the app."""
    with app.app_context():
        original = db.engine
        schema = "referral_test_" + uuid4().hex
        with original.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = original.execution_options(schema_translate_map={None: schema})
        db.metadata.create_all(engine)
        db.engines[None] = engine
        try:
            yield engine
        finally:
            db.session.remove()
            db.engines[None] = original
            with original.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def create_user(engine, uid="owner", **values):
    with Session(engine) as tx, tx.begin():
        user = User(id=uid, email=values.pop("email", f"{uid}@example.test"), **values)
        tx.add(user)
        tx.flush()
        code = ensure_profile(tx, uid).code
    return code


def register(engine, uid, code, *, email=None, verified=True, known=False, now=NOW):
    with Session(engine) as tx, tx.begin():
        user = User(id=uid, email=email or f"{uid}@example.test")
        tx.add(user)
        tx.flush()
        register_identity(tx, user, {"email_verified": verified}, True,
                          {"code": code, "captured": now.timestamp()},
                          known_account=known, now=now)


def prediction(engine, uid):
    with Session(engine) as tx, tx.begin():
        row = Prediction(user_id=uid, venue="Test", current_score=80, wickets_fallen=2,
                         overs_remaining=10, predicted_final_score=170, predicted_wickets=5,
                         predicted_next_over_runs=8, next_over_bowler="")
        tx.add(row)
        tx.flush()
        return row.id


def qualify(engine, uid, now=NOW):
    return complete_prediction(uid, prediction(engine, uid), engine=engine, now=now)


def rows(engine, model):
    with Session(engine) as tx:
        return tx.scalars(select(model)).all()


def test_unique_links_and_successful_reward(referral_db):
    engine = referral_db
    code = create_user(engine)
    assert code != create_user(engine, "other")
    register(engine, "new", code)
    assert rows(engine, Referral)[0].status == "pending"
    assert rows(engine, ReferralReward) == []
    assert qualify(engine, "new") == 1
    reward = rows(engine, ReferralReward)[0]
    assert reward.starts_at == NOW
    assert reward.expires_at == datetime(2026, 12, 4, 6)
    assert reward.reward_month == "2026-11"
    assert rows(engine, Referral)[0].status == "rewarded"


def test_referred_friend_gets_30_days_pro_on_signup(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    grant = rows(engine, ReferralWelcomeGrant)[0]
    assert grant.user_id == "new"
    assert grant.starts_at == NOW
    assert grant.expires_at == NOW + timedelta(days=30)
    with Session(engine) as tx:
        assert tx.get(User, "new").pro_expires_at == NOW + timedelta(days=30)


def test_rejected_referral_gets_no_welcome_pro(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code, verified=False)
    assert rows(engine, ReferralWelcomeGrant) == []


def test_retries_and_repeated_predictions_never_reward_twice(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    pid = prediction(engine, "new")
    assert complete_prediction("new", pid, engine, NOW) == 1
    assert complete_prediction("new", pid, engine, NOW) == 0
    assert qualify(engine, "new") == 0
    assert len(rows(engine, ReferralReward)) == 1


def test_cap_month_reset_and_no_lifetime_limit(referral_db):
    engine = referral_db
    code = create_user(engine)
    for i in range(12):
        register(engine, f"new{i}", code)
        qualify(engine, f"new{i}")
    assert len(rows(engine, ReferralReward)) == 5
    assert sum(r.status == "qualified" for r in rows(engine, Referral)) == 7
    assert settle_rewards("owner", engine, datetime(2026, 11, 30, 15, 59, 59)) == 0
    # Midnight 1 December Singapore, still 30 November UTC.
    assert settle_rewards("owner", engine, datetime(2026, 11, 30, 16)) == 5
    assert settle_rewards("owner", engine, datetime(2026, 12, 31, 16)) == 2
    assert len(rows(engine, ReferralReward)) == 12
    assert {r.reward_month for r in rows(engine, ReferralReward)} == {
        "2026-11", "2026-12", "2027-01"}


def test_concurrent_qualifications_cannot_bypass_cap(referral_db):
    engine = referral_db
    code = create_user(engine)
    jobs = []
    for i in range(12):
        uid = f"new{i}"
        register(engine, uid, code)
        jobs.append((uid, prediction(engine, uid)))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda job: complete_prediction(*job, engine=engine, now=NOW), jobs))
    rewards = rows(engine, ReferralReward)
    assert len(rewards) == 5
    assert {r.month_slot for r in rewards} == {1, 2, 3, 4, 5}
    assert len({r.referral_id for r in rewards}) == 5
    ordered = sorted(rewards, key=lambda r: r.starts_at)
    assert all(a.expires_at == b.starts_at for a, b in zip(ordered, ordered[1:]))


def test_concurrent_duplicate_requests_only_reward_once(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    pid = prediction(engine, "new")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: complete_prediction("new", pid, engine, NOW), range(12)))
    assert len(rows(engine, ReferralReward)) == 1


def test_self_referral_and_existing_accounts(referral_db):
    engine = referral_db
    code = create_user(engine)
    with Session(engine) as tx, tx.begin():
        owner = tx.get(User, "owner")
        for is_new in (False, True):
            register_identity(tx, owner, {"email_verified": True}, is_new,
                              {"code": code, "captured": NOW.timestamp()}, now=NOW)
    assert rows(engine, Referral) == []
    other_code = create_user(engine, "other")
    with Session(engine) as tx, tx.begin():
        register_identity(tx, tx.get(User, "owner"), {"email_verified": True}, False,
                          {"code": other_code, "captured": NOW.timestamp()}, now=NOW)
    assert rows(engine, Referral) == []
    with pytest.raises(IntegrityError):
        with Session(engine) as tx, tx.begin():
            tx.add(Referral(referrer_id="owner", referred_id="owner"))


@pytest.mark.parametrize("email", ["old.name@gmail.com", "oldname+new@googlemail.com"])
def test_duplicate_email_alias_of_preprogramme_account_is_rejected(referral_db, email):
    engine = referral_db
    code = create_user(engine)
    create_user(engine, "existing", email="oldname@gmail.com")
    register(engine, "new", code, email=email)
    assert rows(engine, Referral)[0].rejection_reason == "existing_identity"
    assert qualify(engine, "new") == 0


@pytest.mark.parametrize("verified,known,reason", [
    (False, False, "verified_email_required"),
    (None, False, "verified_email_required"),
    (True, True, "previous_account_on_browser"),
])
def test_unverified_or_additional_browser_account_rejected(referral_db, verified, known, reason):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code, verified=verified, known=known)
    assert rows(engine, Referral)[0].rejection_reason == reason
    assert qualify(engine, "new") == 0


def test_same_ip_does_not_disqualify_different_identities(referral_db):
    engine = referral_db
    code = create_user(engine)
    # IP is deliberately not an input to identity validation or qualification.
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "203.0.113.1"}):
        register(engine, "friend1", code)
        register(engine, "friend2", code)
        assert qualify(engine, "friend1") == 1
        assert qualify(engine, "friend2") == 1


def test_stack_after_active_paid_and_earned_expiry(referral_db):
    engine = referral_db
    paid_end = datetime(2027, 1, 31, 12)
    code = create_user(engine, subscription_status="active", subscription_period_end=paid_end, is_pro=True)
    register(engine, "new1", code)
    register(engine, "new2", code)
    qualify(engine, "new1")
    qualify(engine, "new2")
    rewards = sorted(rows(engine, ReferralReward), key=lambda r: r.id)
    assert rewards[0].starts_at == paid_end
    assert rewards[0].expires_at == datetime(2027, 2, 28, 12)
    assert rewards[1].starts_at == rewards[0].expires_at
    assert rewards[1].expires_at == datetime(2027, 3, 28, 12)
    with Session(engine) as tx:
        user = tx.get(User, "owner")
        user.subscription_status = "past_due"
        user.is_pro = False
        assert user.has_pro  # Stripe failure does not delete earned access.
        assert user.pro_expires_at == rewards[-1].expires_at


def test_inactive_paid_plan_does_not_delay_immediate_reward(referral_db):
    engine = referral_db
    code = create_user(engine, subscription_status="past_due",
                       subscription_period_end=datetime(2027, 1, 1))
    register(engine, "new", code)
    qualify(engine, "new")
    assert rows(engine, ReferralReward)[0].starts_at == NOW


@pytest.mark.parametrize("value,expected", [
    (datetime(2027, 1, 31, 10), datetime(2027, 2, 28, 10)),
    (datetime(2028, 1, 31, 10), datetime(2028, 2, 29, 10)),
    (datetime(2026, 12, 31, 12), datetime(2027, 1, 31, 12)),
    # Singapore date is 31 January, even though UTC date is still 30 January.
    (datetime(2027, 1, 30, 18), datetime(2027, 2, 27, 18)),
])
def test_month_end_calculations(value, expected):
    assert add_pro_month(value) == expected


def test_singapore_calendar_boundary():
    assert singapore_month(datetime(2026, 11, 30, 15, 59, 59)) == "2026-11"
    assert singapore_month(datetime(2026, 11, 30, 16)) == "2026-12"
    assert canonical_email(" Old.Name+alias@GoogleMail.com ") == "oldname@gmail.com"
    assert canonical_email("different.name+tag@example.test") == "different.name+tag@example.test"


def test_no_saved_prediction_or_wrong_owner_cannot_qualify(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    wrong_pid = prediction(engine, "owner")
    for pid in (999999, wrong_pid):
        with pytest.raises(ValueError):
            complete_prediction("new", pid, engine, NOW)
    assert rows(engine, Referral)[0].status == "pending"
    assert rows(engine, ReferralReward) == []


def test_transaction_rolls_back_when_reward_insert_fails(referral_db, monkeypatch):
    import referrals
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    monkeypatch.setattr(referrals, "add_pro_month", lambda value: value)
    with pytest.raises(IntegrityError):
        qualify(engine, "new")
    assert rows(engine, Referral)[0].status == "pending"
    assert rows(engine, ReferralReward) == []


def test_signed_attribution_registration_round_trip_and_dashboard(referral_db, monkeypatch):
    from flask import g, session
    from replit_auth import save_user
    import replit_auth
    engine = referral_db
    code = create_user(engine)
    client = app.test_client()
    assert client.get(f"/r/{code}").status_code == 302
    with client.session_transaction() as state:
        attribution = dict(state["referral_attribution"])
    with app.test_request_context("/auth/authorized"):
        session["referral_attribution"] = attribution
        user = save_user({"sub": "new", "email": "new@example.test", "email_verified": True})
        assert user.id == "new"
        assert "referral_attribution" not in session
        assert session["referral_known_account"]
    assert rows(engine, Referral)[0].status == "pending"
    qualify(engine, "new", now=datetime.utcnow())
    # Dashboard uses existing login guard; supply a valid existing OAuth token fixture.
    monkeypatch.setattr(replit_auth, "replit", type("Auth", (), {"token": {"expires_in": 3600}})())
    with client.session_transaction() as state:
        state["_user_id"] = "owner"
        state["_fresh"] = True
    g.pop("_login_user", None)  # Fixture's outer app context outlives individual requests.
    response = client.get("/referrals")
    assert response.status_code == 200
    assert f"/r/{code}".encode() in response.data
    assert b'id="copyReferralLink"' in response.data
    assert b"Share" in response.data
    assert b"Pro month awarded" in response.data
    assert b"new@example.test" not in response.data
    assert client.get("/pro/predictions").status_code == 200


def test_expired_attribution_and_authenticated_user_cannot_change_referrer(referral_db):
    from flask import session
    from replit_auth import save_user
    engine = referral_db
    code = create_user(engine)
    client = app.test_client()
    with client.session_transaction() as state:
        state["_user_id"] = "owner"
    client.get(f"/r/{code}")
    with client.session_transaction() as state:
        assert "referral_attribution" not in state
    with app.test_request_context("/auth/authorized"):
        session["referral_attribution"] = {
            "code": code, "captured": (datetime.utcnow() - timedelta(days=31)).timestamp()}
        save_user({"sub": "expired", "email": "expired@example.test", "email_verified": True})
    assert rows(engine, Referral) == []


def test_authenticated_prediction_requires_csrf_and_demo_does_not_reward(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code, now=datetime.utcnow())
    client = app.test_client()
    with client.session_transaction() as state:
        state["_user_id"] = "new"
        state["_fresh"] = True
    assert client.post("/predict", data={"current_score": 80}).status_code == 400
    assert client.get("/demo").status_code == 200
    assert rows(engine, ReferralReward) == []
    assert rows(engine, Referral)[0].status == "pending"
    with client.session_transaction() as state:
        csrf = state["prediction_csrf"]
    from prediction import ALL_VENUES
    valid = {
        "prediction_csrf": csrf, "venue": ALL_VENUES[0], "current_score": "80",
        "wickets_fallen": "2", "overs_completed": "10", "innings": "1",
        "match_format": "mens_t20", "batsman1_name": "Virat Kohli",
        "batsman1_runs": "40", "batsman1_balls": "28",
        # Forged reward/account fields must have no effect.
        "referrer_id": "new", "reward_months": "100", "user_id": "owner",
    }
    assert client.post("/predict", data={**valid, "current_score": "-1"}).status_code == 302
    assert rows(engine, ReferralReward) == []
    result = client.post("/predict", data=valid)
    assert result.status_code == 200
    assert len(rows(engine, ReferralReward)) == 1
    assert rows(engine, ReferralReward)[0].referrer_id == "owner"
    assert rows(engine, Referral)[0].status == "rewarded"
    assert len([p for p in rows(engine, Prediction) if p.user_id == "new"]) == 1


def test_simultaneous_duplicate_identity_registrations(referral_db):
    engine = referral_db
    code = create_user(engine)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda i: register(engine, f"new{i}", code,
                                        email=f"new.person+{i}@gmail.com"), range(2)))
    referrals = rows(engine, Referral)
    assert sum(r.status == "pending" for r in referrals) == 1
    assert sum(r.rejection_reason == "existing_identity" for r in referrals) == 1


def test_expired_rewards_do_not_grant_access_and_db_uniqueness(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    qualify(engine, "new", now=datetime(2020, 1, 1))
    with Session(engine) as tx:
        assert not tx.get(User, "owner").has_pro
    reward = rows(engine, ReferralReward)[0]
    with pytest.raises(IntegrityError):
        with Session(engine) as tx, tx.begin():
            tx.add(ReferralReward(referral_id=reward.referral_id, referrer_id="owner",
                                  reward_month="2021-01", month_slot=1,
                                  awarded_at=NOW, starts_at=NOW,
                                  expires_at=NOW + timedelta(days=30)))
    with pytest.raises(IntegrityError):
        with Session(engine) as tx, tx.begin():
            tx.add(Referral(referrer_id="owner", referred_id="new"))


@pytest.mark.parametrize("verified", [True, False, None, "true"])
def test_provider_verified_identity_is_authoritative(monkeypatch, verified):
    import jwt
    import replit_auth
    from unittest.mock import Mock
    profile = {"sub": "server-user", "email": "server@example.test", "email_verified": verified}
    response = Mock()
    response.json.return_value = profile
    monkeypatch.setattr(replit_auth, "oidc_userinfo_endpoint", lambda issuer: "https://example.test/me")
    monkeypatch.setattr(replit_auth.requests, "get", lambda *args, **kwargs: response)
    claims = replit_auth.authenticated_user_claims({
        "access_token": "test-only",
        "id_token": jwt.encode({"sub": "server-user", "email": "forged@example.test",
                                "email_verified": True}, "test-only-key-not-used-for-auth"),
    })
    assert claims["email"] == "server@example.test"
    assert claims["email_verified"] is (verified is True)
    profile["sub"] = "different-user"
    with pytest.raises(ValueError, match="mismatch"):
        replit_auth.authenticated_user_claims({
            "access_token": "test-only",
            "id_token": jwt.encode({"sub": "server-user"}, "test-only-key-not-used-for-auth"),
        })


def test_copy_and_share_controls():
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the dashboard JavaScript controls")
    subprocess.run([node, "tests/referral_controls.cjs"], check=True, capture_output=True, text=True)


def test_hourly_sweep_recovers_saved_prediction_and_settles_queue(referral_db, monkeypatch):
    import referrals
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    prediction(engine, "new")  # Simulates successful prediction followed by processing failure.
    monkeypatch.setattr(referrals, "utc_now", lambda: NOW)
    referrals.settle_pending_rewards()
    assert len(rows(engine, ReferralReward)) == 1
    referrals.settle_pending_rewards()
    assert len(rows(engine, ReferralReward)) == 1


def test_profile_codes_stay_stable_and_invalid_link_never_attributes(referral_db):
    engine = referral_db
    code = create_user(engine)
    with Session(engine) as tx, tx.begin():
        assert ensure_profile(tx, "owner").code == code
    client = app.test_client()
    assert client.get("/r/not-a-valid-code").status_code == 302
    with client.session_transaction() as state:
        assert "referral_attribution" not in state


def test_database_enforces_cap_slot_bounds(referral_db):
    engine = referral_db
    code = create_user(engine)
    register(engine, "new", code)
    referral = rows(engine, Referral)[0]
    with pytest.raises(IntegrityError):
        with Session(engine) as tx, tx.begin():
            tx.add(ReferralReward(referral_id=referral.id, referrer_id="owner",
                                  reward_month="2026-11", month_slot=6,
                                  awarded_at=NOW, starts_at=NOW,
                                  expires_at=NOW + timedelta(days=30)))
