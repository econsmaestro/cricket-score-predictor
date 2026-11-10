"""Optional "Continue with Google" sign-in (OpenID Connect) alongside Replit sign-in.

Enabled only when GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET (or GOOGLE_OAUTH_CLIENT_ID/
GOOGLE_OAUTH_CLIENT_SECRET) are set. Register
https://<your-domain>/auth/google/authorized as an authorized redirect URI in Google Cloud.
"""
import os

import jwt
import requests
from flask import render_template
from flask_dance.consumer import OAuth2ConsumerBlueprint

GOOGLE_PREFIX = "google:"  # keeps Google "sub" values from colliding with Replit user ids
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"


def _credential(name):
    """Accept GOOGLE_CLIENT_* or the GOOGLE_OAUTH_CLIENT_* names Replit's secrets form uses."""
    return os.environ.get(f"GOOGLE_{name}") or os.environ.get(f"GOOGLE_OAUTH_{name}")


def google_configured():
    return bool(_credential("CLIENT_ID") and _credential("CLIENT_SECRET"))


def make_google_blueprint():
    from replit_auth import UserSessionStorage
    bp = OAuth2ConsumerBlueprint(
        "google_auth", __name__,
        client_id=_credential("CLIENT_ID"),
        client_secret=_credential("CLIENT_SECRET"),
        base_url="https://openidconnect.googleapis.com/",
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        authorization_url_params={"prompt": "select_account"},
        token_url="https://oauth2.googleapis.com/token",
        scope=["openid", "email", "profile"],
        use_pkce=True, code_challenge_method="S256",
        storage=UserSessionStorage(),
    )
    return bp


def google_user_claims(token):
    """Identity, email and verification come from Google's authenticated UserInfo response."""
    response = requests.get(GOOGLE_USERINFO, headers={
        "Authorization": "Bearer " + token["access_token"]}, timeout=10)
    response.raise_for_status()
    claims = response.json()
    id_claims = jwt.decode(token["id_token"], options={"verify_signature": False})
    if not claims.get("sub") or claims["sub"] != id_claims.get("sub"):
        raise ValueError("UserInfo subject mismatch")
    return {
        "sub": GOOGLE_PREFIX + claims["sub"],
        "email": claims.get("email"),
        "email_verified": claims.get("email_verified") is True,
        "first_name": claims.get("given_name"),
        "last_name": claims.get("family_name"),
        "profile_image_url": claims.get("picture"),
    }


def init_google_auth(app):
    """Register the Google blueprint (if configured) and the sign-in chooser page."""
    if google_configured():
        app.register_blueprint(make_google_blueprint(), url_prefix="/auth/google")

    @app.route("/auth/signin")
    def signin_chooser():
        return render_template("signin.html", google_enabled=google_configured())
