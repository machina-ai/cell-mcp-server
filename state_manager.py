import abc
import logging
import threading
from typing import Any, Optional

import redis

import time
from config import REDIS_AUTH, REDIS_HOST, REDIS_PORT, REDIS_TTL_SECONDS

# Default TTL for conversation threads in seconds (e.g., 3 hours)
# This is used by the Redis backend. The in-memory backend is ephemeral.
CONVERSATION_TTL_SECONDS = REDIS_TTL_SECONDS

logger = logging.getLogger(__name__)


class StateBackend(abc.ABC):
    """Abstract base class for state management backends."""

    @abc.abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Retrieve a string value by key."""
        pass

    @abc.abstractmethod
    def setex(self, key: str, ttl_seconds: int, value: str):
        """Set a string value for a key with a TTL (redis-py compatible)."""
        pass

    @abc.abstractmethod
    def delete(self, key: str):
        """Delete a key."""
        pass


class InMemoryStateBackend(StateBackend):
    """In-memory state management using a thread-safe dictionary."""

    def __init__(self):
        self._data: dict[str, str] = {}
        self._lock = threading.Lock()
        # TTLs are not implemented for in-memory, as it's session-based.
        logger.info("Initialized InMemoryStateBackend for conversation state.")

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            return self._data.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str):
        with self._lock:
            self._data[key] = value

    def delete(self, key: str):
        with self._lock:
            if key in self._data:
                del self._data[key]


class RedisStateBackend(StateBackend):
    """Redis-backed state management using a connection pool."""

    def __init__(self, redis_client: redis.Redis):
        self._client = redis_client
        logger.info("RedisStateBackend initialized and connected.")

    def get(self, key: str) -> Optional[str]:
        try:
            return self._client.get(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis GET failed for key '{key}': {e}")
            # In a high-availability setup, you might trigger a reconnect here
            return None

    def setex(self, key: str, ttl_seconds: int, value: str):
        try:
            self._client.setex(key, ttl_seconds, value)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis SETEX failed for key '{key}': {e}")

    def delete(self, key: str):
        try:
            self._client.delete(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis DELETE failed for key '{key}': {e}")


def _create_state_manager() -> StateBackend:
    """Factory function to create the appropriate state manager."""
    if REDIS_HOST:
        try:
            # Use a connection pool for efficient, thread-safe connection management
            pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_AUTH,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            redis_client = redis.Redis(connection_pool=pool)

            # Synchronously verify the connection on startup
            redis_client.ping()
            
            logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}.")
            return RedisStateBackend(redis_client)
        except redis.exceptions.ConnectionError as e:
            logger.error(
                f"Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}. "
                f"Falling back to in-memory state. Error: {e}"
            )
            return InMemoryStateBackend()
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during Redis client setup. "
                f"Falling back to in-memory state. Error: {e}"
            )
            return InMemoryStateBackend()
    else:
        # REDIS_HOST is not set, use the default in-memory backend
        return InMemoryStateBackend()


# Singleton instance of the state manager for the application to use
state_manager = _create_state_manager()