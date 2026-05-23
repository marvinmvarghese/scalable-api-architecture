import time
import logging
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException, status
import redis.asyncio as aioredis
from backend.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, requests_per_sec: int = 100):
        self.requests_per_sec = requests_per_sec
        # In-memory fallback if Redis is unavailable: {ip: [timestamps]}
        self.in_memory_buckets: Dict[str, list] = {}
        self.redis_client: Optional[aioredis.Redis] = None
        self._init_redis()

    def _init_redis(self):
        try:
            self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.error(f"Rate Limiter unable to connect to Redis: {e}. Using in-memory fallback.")
            self.redis_client = None

    async def is_rate_limited(self, ip: str) -> bool:
        """
        Returns True if the IP is rate limited (exceeds requests_per_sec), False otherwise.
        """
        now = time.time()
        
        # 1. Use Redis rate limiting if available
        if self.redis_client:
            try:
                # Key structure: rate:{ip}:{second_timestamp}
                current_bucket = int(now)
                key = f"rate:{ip}:{current_bucket}"
                
                # Use a pipeline to increment and set TTL atomically
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, 2)
                results = await pipe.execute()
                
                request_count = results[0]
                if request_count > self.requests_per_sec:
                    return True
                return False
            except Exception as e:
                logger.warning(f"Redis rate limiter failed: {e}. Falling back to in-memory.")

        # 2. In-memory sliding window fallback
        if ip not in self.in_memory_buckets:
            self.in_memory_buckets[ip] = []
            
        # Clean older requests outside the 1-second window
        window_start = now - 1.0
        self.in_memory_buckets[ip] = [t for t in self.in_memory_buckets[ip] if t > window_start]
        
        if len(self.in_memory_buckets[ip]) >= self.requests_per_sec:
            return True
            
        self.in_memory_buckets[ip].append(now)
        return False

# Initialize a global rate limiter instance
limiter = RateLimiter(requests_per_sec=100)  # 100 requests per second per IP
