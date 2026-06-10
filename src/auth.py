from __future__ import annotations

# Google OAuth login (Authlib) — issues a signed Flask session cookie identifying the user.
#
#   init_auth(app)        registers the Google OAuth client and the auth blueprint on the Flask app
#   login_required(fn)    decorator — returns 401 if no user is logged in
#   current_user_id()     returns the logged-in user's internal id, or None

import logging
from functools import wraps

from flask import Blueprint, jsonify, redirect, session
from authlib.integrations.flask_client import OAuth

from config.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, APP_BASE_URL
from src.database import get_or_create_user, get_user_by_id

logger = logging.getLogger(__name__)

oauth = OAuth()
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def init_auth(app) -> None:
    oauth.init_app(app)
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        client_kwargs={"scope": "openid email profile"},
    )
    app.register_blueprint(auth_bp)


@auth_bp.route("/login/google")
def login_google():
    redirect_uri = f"{APP_BASE_URL}/api/auth/callback/google"
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/callback/google")
def callback_google():
    token = oauth.google.authorize_access_token()
    userinfo = token["userinfo"]

    user = get_or_create_user(
        provider="google",
        provider_sub=userinfo["sub"],
        email=userinfo["email"],
        name=userinfo.get("name", ""),
    )
    session["user_id"] = user["id"]
    return redirect("/")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_bp.route("/me")
def me():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "not authenticated"}), 401

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return jsonify({"error": "not authenticated"}), 401

    return jsonify({"id": user["id"], "email": user["email"], "name": user["name"]})


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "not authenticated"}), 401
        return fn(*args, **kwargs)
    return wrapper


def current_user_id() -> int | None:
    return session.get("user_id")
