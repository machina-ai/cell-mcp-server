from __future__ import annotations

from contextvars import ContextVar
from typing import Mapping

from opentelemetry.baggage import get_baggage
import jwt


_current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def set_current_user_id(user_id: str | None) -> None:
    """Set the current user id in context."""
    _current_user_id.set(user_id)


def current_user_id() -> str | None:
    """Return the current user id from context or tracing baggage."""
    user = _current_user_id.get()
    if user is not None:
        return user
    return get_baggage("user.id")


def extract_user_id_from_headers(headers: Mapping[str, str]) -> str | None:
    """Extract the user id from a JWT Authorization header if present.

    The "email" claim is used if available, otherwise the "sub" claim is
    returned.
    """
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None
    return payload.get("email") or payload.get("sub")
