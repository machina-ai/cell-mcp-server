"""
Unified storage backend for conversation threads.

This module provides a unified interface for accessing the conversation storage backend.
It dynamically selects between Redis and a thread-safe in-memory store based on
the presence of the REDIS_HOST environment variable.

This approach allows for flexible deployment:
- In production environments, Redis is used for robust, persistent storage.
- In local/testing environments, a simple in-memory store is used, avoiding
  the need for a separate Redis instance.

The get_storage_backend() function is the single entry point for accessing the
storage backend, ensuring consistent behavior across the application.
"""

import logging
import threading
import time
from typing import Optional

import config
from utils.env import get_env

logger = logging.getLogger(__name__)

# Try to import Redis, but don't fail if it's not installed.
# The Redis client is only required if REDIS_HOST is set.
try:
    import redis
except ImportError:
    redis = None


class InMemoryStorage:
    """Thread-safe in-memory storage for conversation threads."""

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = max(300, config.REDIS_TTL_SECONDS // 10)
        self._shutdown = False
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info(
            f"In-memory storage initialized with {config.REDIS_TTL_SECONDS}s timeout, "
            f"cleanup every {self._cleanup_interval}s"
        )

    def set_with_ttl(self, key: str, ttl_seconds: int, value: str) -> None:
        """Store value with expiration time."""
        with self._lock:
            expires_at = time.time() + ttl_seconds
            self._store[key] = (value, expires_at)
            logger.debug(f"Stored key {key} with TTL {ttl_seconds}s")

    def get(self, key: str) -> Optional[str]:
        """Retrieve value if not expired."""
        with self._lock:
            if key in self._store:
                value, expires_at = self._store[key]
                if time.time() < expires_at:
                    logger.debug(f"Retrieved key {key}")
                    return value
                else:
                    del self._store[key]
                    logger.debug(f"Key {key} expired and removed")
        return None

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        """Redis-compatible setex method."""
        self.set_with_ttl(key, ttl_seconds, value)

    def _cleanup_worker(self):
        """Background thread that periodically cleans up expired entries."""
        while not self._shutdown:
            time.sleep(self._cleanup_interval)
            self._cleanup_expired()

    def _cleanup_expired(self):
        """Remove all expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [k for k, (_, exp) in self._store.items() if exp < current_time]
            for key in expired_keys:
                del self._store[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired conversation threads")

    def shutdown(self):
        """Graceful shutdown of background thread."""
        self._shutdown = True
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1)


# Global singleton instances for Redis and in-memory storage
_redis_instance = None
_in_memory_instance = None
_storage_lock = threading.Lock()


def get_storage_backend():
    """
    Get the global storage instance (singleton pattern).

    Returns the Redis client if REDIS_HOST is configured, otherwise returns
    an in-memory storage instance.
    """
    global _redis_instance, _in_memory_instance

    if config.REDIS_HOST:
        # Redis is configured, use it
        if not redis:
            raise ImportError(
                "Redis is configured but the 'redis' package is not installed. "
                "Please install it with 'pip install redis'."
            )
        if _redis_instance is None:
            with _storage_lock:
                if _redis_instance is None:
                    try:
                        _redis_instance = redis.Redis(
                            host=config.REDIS_HOST,
                            port=config.REDIS_PORT,
                            password=config.REDIS_AUTH,
                            decode_responses=True,
                        )
                        # Ping the server to ensure a connection can be established
                        _redis_instance.ping()
                        logger.info(f"Connected to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}")
                    except redis.exceptions.ConnectionError as e:
                        logger.error(f"Failed to connect to Redis: {e}")
                        # Fallback to in-memory storage if Redis connection fails
                        _redis_instance = None
                        return get_in_memory_storage()
        return _redis_instance
    else:
        # Redis is not configured, use in-memory storage
        return get_in_memory_storage()


def get_in_memory_storage() -> InMemoryStorage:
    """Get the global in-memory storage instance."""
    global _in_memory_instance
    if _in_memory_instance is None:
        with _storage_lock:
            if _in_memory_instance is None:
                _in_memory_instance = InMemoryStorage()
                logger.info("Initialized in-memory conversation storage (Redis not configured)")
    return _in_memory_instance
