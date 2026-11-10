from uuid import uuid4

import pytest
from sqlalchemy import text

from app import app, db
from models import AuthIdentity, User
from replit_auth import save_google_user, save_user


@pytest.fixture
def auth_db():
    with app.app_context():
        original_engine = db.engine
        schema = "google_auth_test_" + uuid4().hex
        with original_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        test_engine = original_engine.execution_options(
            schema_translate_map={None: schema}
        )
        db.engines[None] = test_engine
        db.metadata.create_all(test_engine)
        try:
            yield test_engine
        finally:
            db.session.remove()
            db.engines[None] = original_engine
            with original_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def google_claims(subject="google-subject", email="new@example.test"):
    return {
        "sub": subject,
        "email": email,
        "email_verified": True,
        "first_name": "Google",
        "last_name": "User",
        "profile_image_url": None,
    }


def test_google_signup_creates_provider_identity_and_cricpredict_account(auth_db):
    with app.test_request_context("/auth/google/authorized"):
        user, is_new = save_google_user(google_claims())

        assert is_new is True
        assert user.id == "google:google-subject"
        identity = AuthIdentity.query.filter_by(
            provider="google", provider_subject="google-subject"
        ).one()
        assert identity.user_id == user.id
        assert identity.email_verified is True


def test_verified_replit_identity_links_google_to_existing_account(auth_db):
    user = User(id="replit-user", email="person@example.test")
    db.session.add(user)
    db.session.flush()
    db.session.add(AuthIdentity(
        user_id=user.id,
        provider="replit_auth",
        provider_subject="replit-subject",
        email="person@example.test",
        email_verified=True,
    ))
    db.session.commit()

    with app.test_request_context("/auth/google/authorized"):
        linked_user, is_new = save_google_user(
            google_claims("google-subject", "PERSON@example.test")
        )

    assert linked_user.id == user.id
    assert is_new is False
    assert AuthIdentity.query.filter_by(
        user_id=user.id, provider="google", provider_subject="google-subject"
    ).one()


def test_replit_signin_reuses_google_created_account(auth_db):
    with app.test_request_context("/auth/google/authorized"):
        google_user, _ = save_google_user(
            google_claims("google-subject", "person@example.test")
        )
        replit_user = save_user({
            "sub": "replit-subject",
            "email": "PERSON@example.test",
            "email_verified": True,
            "first_name": "Replit",
            "last_name": "User",
            "profile_image_url": None,
        })

    assert replit_user.id == google_user.id
    assert AuthIdentity.query.filter_by(
        user_id=google_user.id, provider="replit_auth",
        provider_subject="replit-subject",
    ).one()


def test_google_does_not_auto_link_to_unverified_existing_email(auth_db):
    db.session.add(User(id="replit-user", email="person@example.test"))
    db.session.commit()

    with app.test_request_context("/auth/google/authorized"):
        with pytest.raises(ValueError, match="Sign in with Replit once"):
            save_google_user(google_claims("google-subject", "person@example.test"))

    assert User.query.count() == 1
    assert AuthIdentity.query.count() == 0


def test_google_cannot_be_linked_when_email_belongs_to_another_account(auth_db):
    owner = User(id="current-user", email="current@example.test")
    other = User(id="other-user", email="google@example.test")
    db.session.add_all([owner, other])
    db.session.commit()

    with app.test_request_context("/auth/google/authorized"):
        from flask_login import login_user

        login_user(owner)
        with pytest.raises(ValueError, match="belongs to a different"):
            save_google_user(
                google_claims("google-subject", "google@example.test"),
                link_user_id=owner.id,
            )

    assert AuthIdentity.query.count() == 0


def test_sign_in_page_keeps_replit_available_and_discloses_missing_google_setup(
    client, monkeypatch
):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)

    response = client.get("/sign-in")

    assert response.status_code == 200
    assert b"Continue with Replit" in response.data
    assert b"Google sign-in setup pending" in response.data
