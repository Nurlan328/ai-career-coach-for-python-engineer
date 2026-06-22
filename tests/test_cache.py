def test_memory_cache_roundtrip():
    # Redis is not running in tests, so Cache transparently uses its memory fallback.
    from app.core.cache import Cache

    c = Cache()
    assert c.get("missing") is None
    c.set("k", {"a": 1, "b": [2, 3]}, ttl=60)
    assert c.get("k") == {"a": 1, "b": [2, 3]}
