import jwt
import pytest

import google_auth
from app import app


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def token_for(sub):
    return {"access_token": "at", "id_token": jwt.encode({"sub": sub}, "k" * 32, algorithm="HS256")}


def test_google_claims_are_prefixed_and_verified(monkeypatch):
    monkeypatch.setattr(google_auth.requests, "get", lambda *a, **k: FakeResponse({
        "sub": "123", "email": "a@gmail.com", "email_verified": True,
        "given_name": "A", "family_name": "B", "picture": "http://p"}))
    claims = google_auth.google_user_claims(token_for("123"))
    assert claims["sub"] == "google:123"
    assert claims["email_verified"] is True and claims["first_name"] == "A"


@pytest.mark.parametrize("verified", [False, None, "true"])
def test_google_unverified_email_is_not_trusted(monkeypatch, verified):
    monkeypatch.setattr(google_auth.requests, "get", lambda *a, **k: FakeResponse({
        "sub": "1", "email": "a@gmail.com", "email_verified": verified}))
    assert google_auth.google_user_claims(token_for("1"))["email_verified"] is False


def test_google_subject_mismatch_rejected(monkeypatch):
    monkeypatch.setattr(google_auth.requests, "get", lambda *a, **k: FakeResponse({"sub": "1"}))
    with pytest.raises(ValueError):
        google_auth.google_user_claims(token_for("2"))


def test_signin_chooser_always_offers_replit():
    resp = app.test_client().get("/auth/signin")
    assert resp.status_code == 200 and b"Continue with Replit" in resp.data


def test_accepts_replit_style_secret_names(monkeypatch):
    for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    assert not google_auth.google_configured()
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret")
    assert google_auth.google_configured()


@pytest.mark.parametrize("path", ["/privacy-policy", "/terms"])
def test_legal_pages_render(path):
    resp = app.test_client().get(path)
    assert resp.status_code == 200 and b"Last updated" in resp.data
