import jwt
import os
import posixpath
import uuid
from functools import wraps, lru_cache
from urllib.parse import unquote, urlencode, urlsplit, urlunsplit

from flask import g, session, redirect, request, render_template, url_for, flash
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy
import requests

from app import app, db
from models import AuthIdentity, OAuth, User

login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class UserSessionStorage(BaseStorage):

    def get(self, blueprint):
        try:
            token = db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one().token
        except NoResultFound:
            token = None
        return token

    def set(self, blueprint, token):
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name,
        ).delete()
        new_model = OAuth()
        new_model.user_id = current_user.get_id()
        new_model.browser_session_key = g.browser_session_key
        new_model.provider = blueprint.name
        new_model.token = token
        db.session.add(new_model)
        db.session.commit()

    def delete(self, blueprint):
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name).delete()
        db.session.commit()


def make_replit_blueprint():
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("the REPL_ID environment variable must be set")

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={
            "prompt": "login consent",
        },
        token_url=issuer_url + "/token",
        token_url_params={
            "auth": (),
            "include_client_id": True,
        },
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={
            "client_id": repl_id,
        },
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=UserSessionStorage(),
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session

    @replit_bp.route("/logout")
    def logout():
        had_replit_session = bool(replit_bp.token)
        try:
            del replit_bp.token
        except (NoResultFound, RuntimeError):
            pass
        logout_user()
        session.clear()

        if not had_replit_session:
            return redirect("/")

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id":
            repl_id,
            "post_logout_redirect_uri":
            request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    @replit_bp.route("/error")
    def error():
        return render_template("403.html"), 403

    return replit_bp


def make_google_blueprint():
    """Google is an optional second provider, enabled only after OAuth secrets are set."""
    from flask_dance.contrib.google import make_google_blueprint as google_blueprint

    return google_blueprint(
        client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
        scope=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        reprompt_select_account=True,
        login_url="/google",
        authorized_url="/google/authorized",
    )


def _normalized_email(email):
    return (email or "").strip().casefold()


def _store_auth_identity(user, provider, subject, email, email_verified):
    identity = AuthIdentity.query.filter_by(
        provider=provider, provider_subject=subject
    ).first()
    if identity and identity.user_id != user.id:
        raise ValueError("This sign-in identity is already linked to another account.")

    provider_for_user = AuthIdentity.query.filter_by(
        user_id=user.id, provider=provider
    ).first()
    if provider_for_user and provider_for_user.provider_subject != subject:
        raise ValueError("This account already has a different identity for this provider.")

    if identity is None:
        identity = AuthIdentity(
            user_id=user.id,
            provider=provider,
            provider_subject=subject,
        )
        db.session.add(identity)
    identity.email = email
    identity.email_verified = bool(email_verified)
    return identity


def save_user(user_claims):
    from referrals import register_identity
    subject = user_claims["sub"]
    email = user_claims.get("email")
    identity = AuthIdentity.query.filter_by(
        provider="replit_auth", provider_subject=subject
    ).first()
    user = db.session.get(User, identity.user_id) if identity else db.session.get(User, subject)
    is_new = user is None

    if user is None and email:
        matching_user = User.query.filter(
            db.func.lower(User.email) == _normalized_email(email)
        ).first()
        if matching_user:
            trusted_identity = None
            if user_claims.get("email_verified") is True:
                trusted_identity = AuthIdentity.query.filter_by(
                    user_id=matching_user.id, email_verified=True
                ).filter(
                    db.func.lower(AuthIdentity.email) == _normalized_email(email)
                ).first()
            if not trusted_identity:
                raise ValueError(
                    "An account with this email already exists; sign in with its linked provider."
                )
            user = matching_user
            is_new = False

    if user is None:
        user = User(id=subject)
        db.session.add(user)
    if email and (not user.email or _normalized_email(user.email) == _normalized_email(email)):
        user.email = email
    user.first_name = user_claims.get("first_name") or user.first_name
    user.last_name = user_claims.get("last_name") or user.last_name
    user.profile_image_url = user_claims.get("profile_image_url") or user.profile_image_url
    db.session.flush()
    _store_auth_identity(
        user, "replit_auth", subject, email, user_claims.get("email_verified") is True
    )
    register_identity(
        db.session, user, user_claims, is_new,
        session.get("referral_attribution"),
        known_account=bool(session.get("referral_known_account")),
    )
    db.session.commit()
    session.pop("referral_attribution", None)
    session["referral_known_account"] = True
    session["auth_provider"] = "replit_auth"
    return user


def authenticated_google_claims(token):
    response = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": "Bearer " + token["access_token"]},
        timeout=10,
    )
    response.raise_for_status()
    claims = response.json()
    if not claims.get("sub") or not claims.get("email") or claims.get("email_verified") is not True:
        raise ValueError("Google must return a verified email address.")
    return {
        "sub": claims["sub"],
        "email": claims["email"],
        "email_verified": True,
        "first_name": claims.get("given_name"),
        "last_name": claims.get("family_name"),
        "profile_image_url": claims.get("picture"),
    }


def save_google_user(user_claims, link_user_id=None):
    from referrals import register_identity

    subject = user_claims["sub"]
    email = user_claims["email"]
    identity = AuthIdentity.query.filter_by(
        provider="google", provider_subject=subject
    ).first()
    is_new = False

    if link_user_id:
        user = db.session.get(User, link_user_id)
        if user is None or not current_user.is_authenticated or current_user.id != user.id:
            raise ValueError("The account to link is no longer signed in.")
        email_owner = User.query.filter(
            db.func.lower(User.email) == _normalized_email(email)
        ).first()
        if email_owner and email_owner.id != user.id:
            raise ValueError("That Google email belongs to a different CricPredict account.")
        _store_auth_identity(user, "google", subject, email, True)
    elif identity:
        user = db.session.get(User, identity.user_id)
        if user is None:
            raise ValueError("The linked CricPredict account no longer exists.")
    else:
        normalized = _normalized_email(email)
        matching_user = User.query.filter(
            db.func.lower(User.email) == normalized
        ).first()
        if matching_user:
            verified_identity = AuthIdentity.query.filter_by(
                user_id=matching_user.id, email_verified=True
            ).filter(db.func.lower(AuthIdentity.email) == normalized).first()
            if not verified_identity:
                raise ValueError(
                    "This email already has an account. Sign in with Replit once, "
                    "then use Connect Google to link it safely."
                )
            user = matching_user
            _store_auth_identity(user, "google", subject, email, True)
        else:
            is_new = True
            user = User(
                id=f"google:{subject}",
                email=email,
                first_name=user_claims.get("first_name"),
                last_name=user_claims.get("last_name"),
                profile_image_url=user_claims.get("profile_image_url"),
            )
            db.session.add(user)
            db.session.flush()
            _store_auth_identity(user, "google", subject, email, True)

    if link_user_id:
        db.session.commit()
        return user, False

    register_identity(
        db.session, user, user_claims, is_new,
        session.get("referral_attribution"),
        known_account=bool(session.get("referral_known_account")),
    )
    db.session.commit()
    if is_new:
        session.pop("referral_attribution", None)
    session["referral_known_account"] = True
    session["auth_provider"] = "google"
    return user, is_new


def safe_next_url(value):
    """Return a local destination, excluding sign-in loops and external redirects."""
    if not isinstance(value, str) or not value or value != value.strip():
        return "/"
    if "\\" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return "/"
    try:
        target = urlsplit(value)
        origin = urlsplit(request.host_url)
        if target.scheme or target.netloc:
            if (target.scheme.lower(), target.netloc.lower()) != (
                origin.scheme.lower(), origin.netloc.lower()
            ):
                return "/"
        path = target.path or "/"
        decoded = path
        for _ in range(5):
            previous = decoded
            decoded = unquote(decoded)
            if decoded == previous:
                break
        else:
            return "/"
        if (
            not path.startswith("/") or path.startswith("//")
            or decoded.startswith("//") or "\\" in decoded
            or any(ord(char) < 32 or ord(char) == 127 for char in decoded)
        ):
            return "/"
        normalized = posixpath.normpath(decoded)
        if normalized in ("/sign-in", "/auth") or normalized.startswith("/auth/"):
            return "/"
        return urlunsplit(("", "", path, target.query, target.fragment))
    except ValueError:
        return "/"


@oauth_authorized.connect
def logged_in(blueprint, token):
    if blueprint.name == "google":
        try:
            claims = authenticated_google_claims(token)
            link_user_id = session.pop("google_link_user_id", None)
            user, _ = save_google_user(claims, link_user_id=link_user_id)
        except (requests.RequestException, ValueError, KeyError) as exc:
            db.session.rollback()
            app.logger.info("Google sign-in could not be completed: %s", exc)
            flash(str(exc), "error")
            return redirect(url_for("auth_options"))
        if link_user_id:
            flash("Google has been linked to your CricPredict account.", "success")
        else:
            login_user(user)
            flash("You're signed in.", "success")
        next_url = session.pop("next_url", None)
        return redirect(safe_next_url(next_url))

    if blueprint.name != "replit_auth":
        return
    try:
        user_claims = authenticated_user_claims(token)
    except (requests.RequestException, ValueError, KeyError, jwt.PyJWTError):
        app.logger.warning("Authentication provider identity validation failed")
        return redirect(url_for('replit_auth.error'))
    try:
        user = save_user(user_claims)
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "error")
        return redirect(url_for("auth_options"))
    login_user(user)
    blueprint.token = token
    flash("You're signed in.", "success")
    next_url = session.pop("next_url", None)
    return redirect(safe_next_url(next_url))


@lru_cache(maxsize=4)
def oidc_userinfo_endpoint(issuer):
    response = requests.get(issuer.rstrip("/") + "/.well-known/openid-configuration", timeout=10)
    response.raise_for_status()
    metadata = response.json()
    if metadata.get("issuer") != issuer or not metadata.get("userinfo_endpoint", "").startswith("https://"):
        raise ValueError("Invalid authentication provider configuration")
    return metadata["userinfo_endpoint"]


def authenticated_user_claims(token):
    """Use the provider's authenticated UserInfo response, not client-supplied claims.

    This also confirms email verification for referral eligibility without adding
    a new identity provider or JWT cryptography dependency.
    """
    issuer = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
    endpoint = oidc_userinfo_endpoint(issuer)
    response = requests.get(endpoint, headers={
        "Authorization": "Bearer " + token["access_token"],
    }, timeout=10)
    response.raise_for_status()
    claims = response.json()
    id_claims = jwt.decode(token["id_token"], options={"verify_signature": False})
    if not claims.get("sub") or claims["sub"] != id_claims.get("sub"):
        raise ValueError("UserInfo subject mismatch")
    # The ID token supplies presentation details only. Identity, email and
    # verified status must come from the authenticated provider response.
    return {
        "sub": claims["sub"],
        "email": claims.get("email"),
        "email_verified": claims.get("email_verified") is True,
        "first_name": claims.get("first_name", id_claims.get("first_name")),
        "last_name": claims.get("last_name", id_claims.get("last_name")),
        "profile_image_url": claims.get("profile_image_url", id_claims.get("profile_image_url")),
    }


@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    if blueprint.name == "google":
        session.pop("google_link_user_id", None)
        flash("Google sign-in was cancelled or could not be completed. Please try again.", "error")
        return redirect(url_for("auth_options"))
    return redirect(url_for('replit_auth.error'))


def require_login(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = safe_next_url(get_next_navigation_url(request))
            return redirect(url_for('auth_options'))

        # Google login establishes a CricPredict session independently of Replit.
        # An old Replit token must not invalidate that session.
        if session.get("auth_provider") == "google":
            return f(*args, **kwargs)

        token = replit.token
        expires_in = token.get('expires_in', 0) if token else 0
        if expires_in < 0:
            issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
            refresh_token_url = issuer_url + "/token"
            try:
                token = replit.refresh_token(token_url=refresh_token_url,
                                             client_id=os.environ['REPL_ID'])
            except InvalidGrantError:
                # Clear the failed login before /sign-in checks authentication,
                # otherwise it redirects back here indefinitely.
                del replit.token
                logout_user()
                session.pop("auth_provider", None)
                session["next_url"] = safe_next_url(request.full_path.rstrip("?"))
                flash("Your sign-in session has expired. Please sign in again.", "warning")
                return redirect(url_for('auth_options'))
            replit.token_updater(token)

        return f(*args, **kwargs)

    return decorated_function


def get_next_navigation_url(request):
    is_navigation_url = request.headers.get(
        'Sec-Fetch-Mode') == 'navigate' and request.headers.get(
            'Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url


replit = LocalProxy(lambda: g.flask_dance_replit)
