from types import SimpleNamespace

import pytest
from flask import get_flashed_messages, session

from app import app
from models import User
import replit_auth
import routes


DESTINATIONS = [
    (None, "/"),
    ("", "/"),
    ("/pricing?from=login", "/pricing?from=login"),
    ("https://localhost/referrals", "/referrals"),
    ("/sign-in", "/"),
    ("/sign-in/?next=/pricing", "/"),
    ("https://localhost/sign-in", "/"),
    ("/auth/google/authorized", "/"),
    ("/auth/replit_auth", "/"),
    ("/auth", "/"),
    ("/%61uth/google", "/"),
    ("/foo/../auth/google", "/"),
    ("/%2573ign-in", "/"),
    ("https://evil.example/pricing", "/"),
    ("https://localhost.evil.example/pricing", "/"),
    ("https://localhost@evil.example/pricing", "/"),
    ("//evil.example/pricing", "/"),
    ("//localhost/pricing", "/"),
    ("https://localhost//evil.example", "/"),
    ("/%2fevil.example", "/"),
    ("/\\evil.example", "/"),
    ("javascript:alert(1)", "/"),
    ("pricing", "/"),
    ("/pricing\n", "/"),
    ("/%0d%0aLocation:evil", "/"),
]


@pytest.mark.parametrize("provider", ["google", "replit_auth"])
@pytest.mark.parametrize("destination,expected", DESTINATIONS)
def test_login_redirect_is_safe_and_announces_success(monkeypatch, provider, destination, expected):
    user = User(id="navigation-test-user")
    monkeypatch.setattr(replit_auth, "authenticated_google_claims", lambda token: {})
    monkeypatch.setattr(replit_auth, "authenticated_user_claims", lambda token: {})
    monkeypatch.setattr(replit_auth, "save_google_user", lambda claims, **kwargs: (user, False))
    monkeypatch.setattr(replit_auth, "save_user", lambda claims: user)
    blueprint = SimpleNamespace(name=provider, token=None)

    with app.test_request_context("/auth/callback", base_url="https://localhost"):
        session["next_url"] = destination
        response = replit_auth.logged_in(blueprint, {"access_token": "synthetic"})

        assert response.status_code == 302
        assert response.location == expected
        assert "next_url" not in session
        assert session["_user_id"] == user.id
        assert ("success", "You're signed in.") in get_flashed_messages(with_categories=True)
        if provider == "replit_auth":
            assert blueprint.token == {"access_token": "synthetic"}


@pytest.mark.parametrize("destination,expected", DESTINATIONS)
def test_authenticated_sign_in_redirects_safely(monkeypatch, destination, expected):
    monkeypatch.setattr(routes, "current_user", SimpleNamespace(is_authenticated=True))
    with app.test_request_context("/sign-in", base_url="https://localhost"):
        session["next_url"] = destination
        response = routes.auth_options()
        assert response.location == expected
        assert "next_url" not in session


def test_authenticated_sign_in_query_overrides_and_clears_stored_next(monkeypatch):
    monkeypatch.setattr(routes, "current_user", SimpleNamespace(is_authenticated=True))
    with app.test_request_context("/sign-in?next=/referrals"):
        session["next_url"] = "/pricing"
        assert routes.auth_options().location == "/referrals"
        assert "next_url" not in session


@pytest.mark.parametrize("destination", ["/auth/google", "//evil.example", "/sign-in"])
def test_authenticated_sign_in_rejects_unsafe_query(monkeypatch, destination):
    monkeypatch.setattr(routes, "current_user", SimpleNamespace(is_authenticated=True))
    with app.test_request_context("/sign-in", query_string={"next": destination}):
        session["next_url"] = "/pricing"
        assert routes.auth_options().location == "/"
        assert "next_url" not in session


def test_anonymous_sign_in_renders_success_flash(client):
    with client.session_transaction() as stored:
        stored["_flashes"] = [("success", "You're signed in.")]
    response = client.get("/sign-in")
    assert response.status_code == 200
    assert b"alert-success" in response.data
    assert b"You&#39;re signed in." in response.data


@pytest.mark.parametrize("destination,expected", [
    ("/referrals", "/referrals"),
    ("/auth/google", "/"),
    ("https://evil.example", "/"),
])
def test_anonymous_sign_in_stores_only_safe_next(client, destination, expected):
    response = client.get("/sign-in", query_string={"next": destination})
    assert response.status_code == 200
    with client.session_transaction() as stored:
        assert stored["next_url"] == expected


def _referral_auth_client(client, monkeypatch, provider):
    """Exercise the real referrals URL and auth guard without referral DB writes."""
    user = User(id="referral-navigation-user")
    monkeypatch.setattr(replit_auth.login_manager, "_user_callback", lambda user_id: user)
    monkeypatch.setitem(
        app.view_functions, "referral_dashboard",
        replit_auth.require_login(lambda: "Referral dashboard"),
    )
    with client.session_transaction() as stored:
        stored["_user_id"] = user.id
        stored["_fresh"] = True
        if provider:
            stored["auth_provider"] = provider


def test_google_referrals_ignores_stale_replit_credentials(client, monkeypatch):
    _referral_auth_client(client, monkeypatch, "google")

    class UnusedReplitSession:
        @property
        def token(self):
            raise AssertionError("Google login must not inspect Replit credentials")

    monkeypatch.setattr(replit_auth, "replit", UnusedReplitSession())
    response = client.get("/referrals", follow_redirects=True)
    assert response.status_code == 200
    assert response.data == b"Referral dashboard"
    assert not response.history


@pytest.mark.parametrize("provider", ["replit_auth", None])
def test_expired_replit_referrals_ends_at_sign_in_without_loop(client, monkeypatch, provider):
    _referral_auth_client(client, monkeypatch, provider)

    class ExpiredReplitSession:
        def __init__(self):
            self.token = {"expires_in": -1, "refresh_token": "synthetic"}

        def refresh_token(self, **kwargs):
            raise replit_auth.InvalidGrantError()

    monkeypatch.setattr(replit_auth, "replit", ExpiredReplitSession())
    response = client.get("/referrals", follow_redirects=True)
    assert response.status_code == 200
    assert response.request.path == "/sign-in"
    assert len(response.history) == 1
    assert b"Please sign in again" in response.data
    with client.session_transaction() as stored:
        assert "_user_id" not in stored
        assert "auth_provider" not in stored
        assert stored["next_url"] == "/referrals"


def test_valid_replit_referrals_still_loads(client, monkeypatch):
    _referral_auth_client(client, monkeypatch, "replit_auth")
    monkeypatch.setattr(
        replit_auth, "replit", SimpleNamespace(token={"expires_in": 600})
    )
    response = client.get("/referrals")
    assert response.status_code == 200
    assert response.data == b"Referral dashboard"


def test_refreshable_replit_referrals_still_loads(client, monkeypatch):
    _referral_auth_client(client, monkeypatch, "replit_auth")
    updated = []
    refreshed = {"expires_in": 600, "access_token": "synthetic"}
    monkeypatch.setattr(replit_auth, "replit", SimpleNamespace(
        token={"expires_in": -1, "refresh_token": "synthetic"},
        refresh_token=lambda **kwargs: refreshed,
        token_updater=updated.append,
    ))
    response = client.get("/referrals")
    assert response.status_code == 200
    assert response.data == b"Referral dashboard"
    assert updated == [refreshed]


def test_anonymous_referrals_reaches_sign_in(client):
    response = client.get("/referrals", follow_redirects=True)
    assert response.status_code == 200
    assert response.request.path == "/sign-in"
    assert len(response.history) == 1
