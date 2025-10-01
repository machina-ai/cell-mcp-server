"""
State management for conversation threads.

This module provides a flexible state management backend for conversation
contexts, adhering to SOLID and KISS principles. It is designed to be a
drop-in replacement for the original storage system with minimal changes
to the existing codebase.

It features:
- An abstract `StateBackend` interface for dependency inversion.
- A `RedisStateBackend` for scalable, persistent storage.
- An `InMemoryStateBackend` that replicates the original in-memory logic
  for seamless fallback and local development.
- A factory function `get_state_backend` that intelligently selects the
  backend based on environment variable configuration.
"""

import abc
import logging
import os
import threading
import time
from typing import Optional

import redis
from config import REDIS_HOST, REDIS_PORT, REDIS_AUTH, REDIS_TTL_SECONDS

logger = logging.getLogger(__name__)


class StateBackend(abc.ABC):
    """Abstract interface for a state management backend."""

    @abc.abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Retrieve a value by key."""
        pass

    @abc.abstractmethod
    def setex(self, key: str, ttl_seconds: int, value: str):
        """Set a value for a key with a TTL."""
        pass

    @abc.abstractmethod
    def delete(self, key: str):
        """Delete a key."""
        pass


class RedisStateBackend(StateBackend):
    """State management backed by a Redis server."""

    def __init__(self, client: redis.Redis):
        self._client = client
        logger.info(f"RedisStateBackend initialized for host {REDIS_HOST}.")

    def get(self, key: str) -> Optional[str]:
        try:
            return self._client.get(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis GET failed for key '{key}': {e}")
            return None

    def setex(self, key: str, ttl_seconds: int, value: str):
        try:
            # Use the globally configured TTL
            self._client.setex(key, REDIS_TTL_SECONDS, value)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis SETEX failed for key '{key}': {e}")

    def delete(self, key: str):
        try:
            self._client.delete(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis DELETE failed for key '{key}': {e}")


class InMemoryStateBackend(StateBackend):
    """
    In-memory state management that replicates the original project's logic.
    This serves as the default fallback if Redis is not configured.
    """

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()
        timeout_hours = int(os.getenv("CONVERSATION_TIMEOUT_HOURS", "3"))
        self._cleanup_interval = max(300, (timeout_hours * 3600) // 10)
        self._shutdown = False
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("InMemoryStateBackend initialized as fallback.")

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._store:
                value, expires_at = self._store[key]
                if time.time() < expires_at:
                    return value
                else:
                    del self._store[key]
        return None

    def setex(self, key: str, ttl_seconds: int, value: str):
        with self._lock:
            expires_at = time.time() + ttl_seconds
            self._store[key] = (value, expires_at)

    def delete(self, key: str):
        with self._lock:
            if key in self._store:
                del self._store[key]

    def _cleanup_worker(self):
        while not self._shutdown:
            time.sleep(self._cleanup_interval)
            with self._lock:
                current_time = time.time()
                expired_keys = [k for k, (_, exp) in self._store.items() if exp < current_time]
                for key in expired_keys:
                    del self._store[key]


# --- Factory and Singleton Instance ---

_state_backend_instance: Optional[StateBackend] = None
_state_backend_lock = threading.Lock()


def get_state_backend() -> StateBackend:
    """
    Factory function to create and return the appropriate state backend singleton.
    If REDIS_HOST is configured, it attempts to connect to Redis.
    Otherwise, it falls back to the in-memory backend.
    """
    global _state_backend_instance
    if _state_backend_instance is None:
        with _state_backend_lock:
            if _state_backend_instance is None:
                if REDIS_HOST:
                    try:
                        client = redis.Redis(
                            host=REDIS_HOST,
                            port=REDIS_PORT,
                            password=REDIS_AUTH,
                            decode_responses=True
                        )
                        client.ping()
                        _state_backend_instance = RedisStateBackend(client)
                    except redis.exceptions.ConnectionError as e:
                        logger.error(
                            f"Could not connect to Redis at {REDIS_HOST}. "
                            f"Falling back to in-memory storage. Error: {e}"
                        )
                        _state_backend_instance = InMemoryStateBackend()
                else:
                    _state_backend_instance = InMemoryStateBackend()
    return _state_backend_instance
