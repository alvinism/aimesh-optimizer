import asyncio

import pytest

from aimesh_optimizer.lock import CooldownActive, CooldownLock, InFlight


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


async def test_first_acquire_succeeds_and_starts_cooldown():
    clock = FakeClock()
    lock = CooldownLock(cooldown_seconds=300, clock=clock)
    async with lock.acquire():
        pass
    assert lock.remaining() == pytest.approx(300.0)


async def test_second_acquire_within_cooldown_raises():
    clock = FakeClock()
    lock = CooldownLock(cooldown_seconds=300, clock=clock)
    async with lock.acquire():
        pass
    clock.advance(60)
    with pytest.raises(CooldownActive) as exc:
        async with lock.acquire():
            pass
    assert exc.value.retry_after_seconds == pytest.approx(240.0)


async def test_acquire_after_cooldown_expires():
    clock = FakeClock()
    lock = CooldownLock(cooldown_seconds=300, clock=clock)
    async with lock.acquire():
        pass
    clock.advance(301)
    async with lock.acquire():
        pass  # second success allowed


async def test_failure_does_not_start_cooldown():
    clock = FakeClock()
    lock = CooldownLock(cooldown_seconds=300, clock=clock)
    with pytest.raises(RuntimeError):
        async with lock.acquire():
            raise RuntimeError("router blew up")
    assert lock.remaining() == 0.0
    # immediate retry should be permitted
    async with lock.acquire():
        pass


async def test_concurrent_request_raises_in_flight():
    clock = FakeClock()
    lock = CooldownLock(cooldown_seconds=300, clock=clock)
    started = asyncio.Event()
    finish = asyncio.Event()

    async def slow_op():
        async with lock.acquire():
            started.set()
            await finish.wait()

    task = asyncio.create_task(slow_op())
    await started.wait()
    with pytest.raises(InFlight):
        async with lock.acquire():
            pass
    finish.set()
    await task


async def test_state_reflects_inflight_and_remaining():
    clock = FakeClock()
    lock = CooldownLock(cooldown_seconds=300, clock=clock)
    state = lock.state()
    assert state.in_flight is False
    assert state.cooldown_remaining_seconds == 0.0

    async with lock.acquire():
        mid = lock.state()
        assert mid.in_flight is True

    clock.advance(120)
    after = lock.state()
    assert after.in_flight is False
    assert after.cooldown_remaining_seconds == pytest.approx(180.0)
