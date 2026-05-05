import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass


class CooldownActive(Exception):
    """Raised when a request arrives within the cooldown window."""

    def __init__(self, retry_after_seconds: float) -> None:
        super().__init__(f"cooldown active, retry in {retry_after_seconds:.0f}s")
        self.retry_after_seconds = retry_after_seconds


class InFlight(Exception):
    """Raised when another optimize is already executing."""


@dataclass
class CooldownState:
    cooldown_remaining_seconds: float
    in_flight: bool


class CooldownLock:
    """Combines an in-flight asyncio.Lock with a post-success cooldown.

    - Concurrent requests during execution → InFlight (HTTP 423).
    - New request within `cooldown_seconds` of last *success* → CooldownActive (HTTP 429).
    - Failed attempts do not start the cooldown — caller can retry immediately.
    """

    def __init__(self, cooldown_seconds: float, *, clock=time.monotonic) -> None:
        self._cooldown = float(cooldown_seconds)
        self._clock = clock
        self._last_success: float | None = None
        self._in_flight = asyncio.Lock()

    def remaining(self) -> float:
        if self._last_success is None:
            return 0.0
        elapsed = self._clock() - self._last_success
        return max(0.0, self._cooldown - elapsed)

    def state(self) -> CooldownState:
        return CooldownState(
            cooldown_remaining_seconds=self.remaining(),
            in_flight=self._in_flight.locked(),
        )

    @asynccontextmanager
    async def acquire(self):
        """Async context manager: acquire the lock or raise.

        On exit *without exception*, the cooldown clock is stamped.
        On exit with exception, the cooldown is left untouched (failure-friendly retry).
        """
        remaining = self.remaining()
        if remaining > 0:
            raise CooldownActive(remaining)
        if self._in_flight.locked():
            raise InFlight()
        await self._in_flight.acquire()
        try:
            yield
        except BaseException:
            self._in_flight.release()
            raise
        else:
            self._last_success = self._clock()
            self._in_flight.release()
