"""
Caching Utilities
Redis-based caching with fallback to in-memory cache
"""

import json
import asyncio
import hashlib
import functools
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Callable, TypeVar, List
from dataclasses import dataclass
from collections import OrderedDict
import pickle

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Try to import redis, provide fallback if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not installed. Using in-memory cache.")

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with value and metadata"""
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    hits: int = 0


class InMemoryCache:
    """
    Simple in-memory LRU cache
    Used as fallback when Redis is not available
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.expires_at and entry.expires_at < datetime.utcnow():
                del self._cache[key]
                return None
            
            # Update access order (LRU)
            self._cache.move_to_end(key)
            entry.hits += 1
            
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set a value in cache"""
        async with self._lock:
            # Remove oldest entries if cache is full
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                expires_at=expires_at
            )
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        async with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry.expires_at and entry.expires_at < datetime.utcnow():
                del self._cache[key]
                return False
            
            return True
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_hits = sum(e.hits for e in self._cache.values())
            return {
                "type": "in_memory",
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": total_hits,
            }


class RedisCache:
    """
    Redis-based cache implementation
    """
    
    def __init__(self, redis_url: str = None, prefix: str = "pm:"):
        self.redis_url = redis_url or settings.REDIS_URL
        self.prefix = prefix
        self._client: Optional[redis.Redis] = None
        self._connected: bool = False
    
    async def connect(self) -> bool:
        """Connect to Redis"""
        if self._connected:
            return True
        
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False  # We'll handle encoding ourselves
            )
            await self._client.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Disconnected from Redis cache")
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if not self._connected:
            return None
        
        try:
            full_key = self._make_key(key)
            data = await self._client.get(full_key)
            
            if data is None:
                return None
            
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set a value in cache"""
        if not self._connected:
            return False
        
        try:
            full_key = self._make_key(key)
            data = pickle.dumps(value)
            
            if ttl_seconds:
                await self._client.setex(full_key, ttl_seconds, data)
            else:
                await self._client.set(full_key, data)
            
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self._connected:
            return False
        
        try:
            full_key = self._make_key(key)
            result = await self._client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._connected:
            return False
        
        try:
            full_key = self._make_key(key)
            return await self._client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def clear(self, pattern: str = "*") -> None:
        """Clear cache entries matching pattern"""
        if not self._connected:
            return
        
        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(cursor, match=full_pattern)
                if keys:
                    await self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._connected:
            return {"type": "redis", "connected": False}
        
        try:
            info = await self._client.info()
            return {
                "type": "redis",
                "connected": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": await self._client.dbsize(),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"type": "redis", "connected": False, "error": str(e)}
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        if not self._connected:
            return None
        
        try:
            full_key = self._make_key(key)
            return await self._client.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return None
    
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set expiration on a key"""
        if not self._connected:
            return False
        
        try:
            full_key = self._make_key(key)
            return await self._client.expire(full_key, ttl_seconds)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False


class CacheManager:
    """
    Cache manager that handles both Redis and in-memory caching
    Automatically falls back to in-memory if Redis is unavailable
    """
    
    def __init__(self, prefer_redis: bool = True):
        self.prefer_redis = prefer_redis
        self._redis_cache: Optional[RedisCache] = None
        self._memory_cache: InMemoryCache = InMemoryCache()
        self._initialized: bool = False
    
    async def initialize(self) -> None:
        """Initialize cache connections"""
        if self._initialized:
            return
        
        if self.prefer_redis and REDIS_AVAILABLE:
            self._redis_cache = RedisCache()
            await self._redis_cache.connect()
        
        self._initialized = True
        logger.info(f"CacheManager initialized (Redis: {self._use_redis})")
    
    @property
    def _use_redis(self) -> bool:
        """Check if Redis should be used"""
        return (
            self._redis_cache is not None and 
            self._redis_cache._connected
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if not self._initialized:
            await self.initialize()
        
        if self._use_redis:
            result = await self._redis_cache.get(key)
            if result is not None:
                return result
        
        return await self._memory_cache.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set a value in cache"""
        if not self._initialized:
            await self.initialize()
        
        success = True
        
        if self._use_redis:
            success = await self._redis_cache.set(key, value, ttl_seconds)
        
        # Also store in memory cache for faster access
        await self._memory_cache.set(key, value, ttl_seconds)
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        if not self._initialized:
            await self.initialize()
        
        success = await self._memory_cache.delete(key)
        
        if self._use_redis:
            success = await self._redis_cache.delete(key) or success
        
        return success
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._initialized:
            await self.initialize()
        
        if self._use_redis:
            if await self._redis_cache.exists(key):
                return True
        
        return await self._memory_cache.exists(key)
    
    async def clear(self, pattern: str = "*") -> None:
        """Clear cache entries"""
        if not self._initialized:
            await self.initialize()
        
        await self._memory_cache.clear()
        
        if self._use_redis:
            await self._redis_cache.clear(pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "memory": await self._memory_cache.get_stats(),
        }
        
        if self._use_redis:
            stats["redis"] = await self._redis_cache.get_stats()
        
        return stats


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache() -> CacheManager:
    """Get or create cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()
    return _cache_manager


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from arguments
    """
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(
    ttl_seconds: int = 300,
    key_prefix: str = "",
    key_builder: Callable = None
):
    """
    Decorator for caching function results
    
    Usage:
        @cached(ttl_seconds=60, key_prefix="user")
        async def get_user(user_id: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                key = cache_key(*args, **kwargs)
            
            full_key = f"{key_prefix}:{func.__name__}:{key}" if key_prefix else f"{func.__name__}:{key}"
            
            # Try to get from cache
            cache = await get_cache()
            cached_value = await cache.get(full_key)
            
            if cached_value is not None:
                logger.debug(f"Cache hit for {full_key}")
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(full_key, result, ttl_seconds)
            logger.debug(f"Cached result for {full_key}")
            
            return result
        
        return wrapper
    return decorator