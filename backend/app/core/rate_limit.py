from hashlib import sha256
from threading import Lock
from time import monotonic

from fastapi import HTTPException, status


class LoginRateLimiter:
    def __init__(
        self,
        *,
        window_seconds: int = 900,
        per_identifier_limit: int = 10,
        per_ip_limit: int = 100,
        max_buckets: int = 20_000,
    ) -> None:
        self.window_seconds = window_seconds
        self.per_identifier_limit = per_identifier_limit
        self.per_ip_limit = per_ip_limit
        self.max_buckets = max_buckets
        self._buckets: dict[str, tuple[int, float]] = {}
        self._last_cleanup = 0.0
        self._lock = Lock()

    def check_and_consume(self, client_ip: str, identifier: str) -> None:
        now = monotonic()
        identity_hash = sha256(identifier.strip().casefold().encode("utf-8")).hexdigest()
        keys = (
            (f"ip:{client_ip}", self.per_ip_limit),
            (f"identity:{identity_hash}", self.per_identifier_limit),
        )

        with self._lock:
            if now - self._last_cleanup >= 60 or len(self._buckets) + len(keys) > self.max_buckets:
                self._buckets = {
                    key: bucket
                    for key, bucket in self._buckets.items()
                    if bucket[1] > now
                }
                self._last_cleanup = now

            retry_after = 0.0
            for key, limit in keys:
                bucket = self._buckets.get(key)
                if bucket is not None and bucket[0] >= limit and bucket[1] > now:
                    retry_after = max(retry_after, bucket[1] - now)
            if retry_after > 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many sign-in attempts. Try again later.",
                    headers={"Retry-After": str(max(1, int(retry_after)))},
                )

            new_buckets = sum(key not in self._buckets for key, _limit in keys)
            if len(self._buckets) + new_buckets > self.max_buckets:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Sign-in is temporarily unavailable. Try again later.",
                )

            for key, _limit in keys:
                count, expiry = self._buckets.get(key, (0, now + self.window_seconds))
                self._buckets[key] = (count + 1, expiry)


login_rate_limiter = LoginRateLimiter()
