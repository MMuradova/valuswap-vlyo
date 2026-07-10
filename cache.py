"""
ValuSwap-VLYO - Redis Keşləmə
"""
import os
import json
from typing import Optional, List

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("MATCH_CACHE_TTL", "60"))

try:
    _client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    _client = None


def _key(product_id: int) -> str:
    return f"valuswap:match:{product_id}"


def get_cached_match(product_id: int) -> Optional[List[dict]]:
    if _client is None:
        return None
    try:
        raw = _client.get(_key(product_id))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_cached_match(product_id: int, matches: List[dict]) -> None:
    if _client is None:
        return
    try:
        _client.setex(_key(product_id), CACHE_TTL_SECONDS, json.dumps(matches))
    except Exception:
        pass


def invalidate_match_cache(product_id: int) -> None:
    if _client is None:
        return
    try:
        _client.delete(_key(product_id))
    except Exception:
        pass