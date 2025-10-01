import abc
import logging
import threading
from typing import Any, Optional

import redis

import time
from config import REDIS_AUTH, REDIS_HOST, REDIS_PORT

# Default TTL for conversation threads in seconds (15 minutes)
# This is used by the Redis backend. The in-memory backend is ephemeral.
CONVERSATION_TTL_SECONDS = 900

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
    """Redis-backed state management with robust connection handling."""

    def __init__(self, redis_client: redis.Redis):
        self._client = redis_client
        self._is_connected = False
        self._lock = threading.Lock()
        self._reconnect_interval = 30  # seconds

        # Start a background thread for connection management
        self._conn_thread = threading.Thread(target=self._connect_and_monitor, daemon=True)
        self._conn_thread.start()
        logger.info("RedisStateBackend initialized; attempting connection in background.")

    def _connect_and_monitor(self):
        """Runs in a background thread to connect and monitor Redis connection."""
        while True:
            try:
                self._client.ping()
                with self._lock:
                    if not self._is_connected:
                        self._is_connected = True
                        logger.info("Successfully connected to Redis.")
            except redis.exceptions.ConnectionError as e:
                with self._lock:
                    if self._is_connected:
                        self._is_connected = False
                        logger.error(f"Lost connection to Redis: {e}. Will attempt to reconnect.")
                    else:
                        # Log less verbosely if we haven't connected yet
                        logger.warning(f"Failed to connect to Redis: {e}. Retrying in {self._reconnect_interval}s.")
            except Exception as e:
                with self._lock:
                    self._is_connected = False
                logger.error(f"An unexpected error occurred in Redis connection thread: {e}")

            time.sleep(self._reconnect_interval)

    @property
    def is_connected(self) -> bool:
        """Thread-safe check for Redis connection status."""
        with self._lock:
            return self._is_connected

    def get(self, key: str) -> Optional[str]:
        if not self.is_connected:
            logger.warning("Redis is not connected. Cannot GET.")
            return None
        try:
            return self._client.get(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis GET failed for key '{key}': {e}")
            return None

    def setex(self, key: str, ttl_seconds: int, value: str):
        if not self.is_connected:
            logger.warning("Redis is not connected. Cannot SETEX.")
            return
        try:
            self._client.setex(key, ttl_seconds, value)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis SETEX failed for key '{key}': {e}")

    def delete(self, key: str):
        if not self.is_connected:
            logger.warning("Redis is not connected. Cannot DELETE.")
            return
        try:
            self._client.delete(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis DELETE failed for key '{key}': {e}")


def _create_state_manager() -> StateBackend:
    """Factory function to create the appropriate state manager."""
    if REDIS_HOST:
        try:
            # Best practice: Use a connection pool for thread-safe connection management
            pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_AUTH,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # The Redis client will manage connections from this pool
            redis_client = redis.Redis(connection_pool=pool)

            logger.info(f"Redis is configured. Initializing RedisStateBackend for {REDIS_HOST}:{REDIS_PORT} with a connection pool.")
            return RedisStateBackend(redis_client)
        except Exception as e:
            # This would catch config errors, not connection errors
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