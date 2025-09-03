from contextvars import ContextVar
from typing import Optional

# Context variables are used to store request-specific state that is available
# across function calls without passing it explicitly as arguments.
# This is the standard way to handle per-request context in modern Python async frameworks.
_user_id_cv: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_session_id_cv: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


def set_session_context(user_id: Optional[str], session_id: Optional[str]) -> None:
    """
    Sets the user_id and session_id for the current request context.
    """
    _user_id_cv.set(user_id)
    _session_id_cv.set(session_id)


def get_user_id() -> Optional[str]:
    """
    Gets the user_id from the current request context.
    """
    return _user_id_cv.get()


def get_session_id() -> Optional[str]:
    """
    Gets the session_id from the current request context.
    """
    return _session_id_cv.get()
