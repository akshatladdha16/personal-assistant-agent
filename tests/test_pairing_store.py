from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.pairing.store import (
    PairingCodeNotFound,
    PairingLimitReached,
    PairingStore,
)


class Clock:
    def __init__(self, start: datetime) -> None:
        self._current = start

    def tick(self, seconds: int) -> None:
        self._current += timedelta(seconds=seconds)

    def __call__(self) -> datetime:
        return self._current


def test_register_request_reuses_existing_code(tmp_path) -> None:
    clock = Clock(datetime(2024, 1, 1, tzinfo=timezone.utc))
    store = PairingStore(
        storage_dir=str(tmp_path),
        clock_fn=clock,
        pending_limit=5,
        code_ttl_seconds=3600,
    )

    req, created = store.register_request(
        user_id=10,
        username="tester",
        first_name="Test",
        last_name="User",
        message_preview="hello",
    )
    assert created is True

    req_again, created_again = store.register_request(
        user_id=10,
        username="tester",
        first_name="Test",
        last_name="User",
        message_preview="hello again",
    )

    assert created_again is False
    assert req_again.code == req.code


def test_pending_limit_enforced(tmp_path) -> None:
    clock = Clock(datetime(2024, 1, 1, tzinfo=timezone.utc))
    store = PairingStore(
        storage_dir=str(tmp_path),
        clock_fn=clock,
        pending_limit=1,
        code_ttl_seconds=3600,
    )

    store.register_request(
        user_id=1,
        username=None,
        first_name=None,
        last_name=None,
        message_preview=None,
    )

    with pytest.raises(PairingLimitReached):
        store.register_request(
            user_id=2,
            username=None,
            first_name=None,
            last_name=None,
            message_preview=None,
        )


def test_expired_requests_are_removed(tmp_path) -> None:
    clock = Clock(datetime(2024, 1, 1, tzinfo=timezone.utc))
    store = PairingStore(
        storage_dir=str(tmp_path),
        clock_fn=clock,
        pending_limit=5,
        code_ttl_seconds=10,
    )

    store.register_request(
        user_id=1,
        username=None,
        first_name=None,
        last_name=None,
        message_preview=None,
    )

    clock.tick(11)

    assert store.list_pending() == []


def test_approve_moves_user_to_allowlist(tmp_path) -> None:
    clock = Clock(datetime(2024, 1, 1, tzinfo=timezone.utc))
    store = PairingStore(
        storage_dir=str(tmp_path),
        clock_fn=clock,
        pending_limit=5,
        code_ttl_seconds=3600,
    )

    req, _ = store.register_request(
        user_id=42,
        username="approved",
        first_name=None,
        last_name=None,
        message_preview=None,
    )

    store.approve(req.code)

    assert store.is_allowed(42) is True
    assert store.list_pending() == []


def test_reject_removes_pending_without_allowing(tmp_path) -> None:
    clock = Clock(datetime(2024, 1, 1, tzinfo=timezone.utc))
    store = PairingStore(
        storage_dir=str(tmp_path),
        clock_fn=clock,
        pending_limit=5,
        code_ttl_seconds=3600,
    )

    req, _ = store.register_request(
        user_id=90,
        username="reject",
        first_name=None,
        last_name=None,
        message_preview=None,
    )

    store.reject(req.code)

    assert store.is_allowed(90) is False
    assert store.list_pending() == []


def test_approving_unknown_code_errors(tmp_path) -> None:
    clock = Clock(datetime(2024, 1, 1, tzinfo=timezone.utc))
    store = PairingStore(
        storage_dir=str(tmp_path),
        clock_fn=clock,
        pending_limit=5,
        code_ttl_seconds=3600,
    )

    with pytest.raises(PairingCodeNotFound):
        store.approve("UNKNOWN")
