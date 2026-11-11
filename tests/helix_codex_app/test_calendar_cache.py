"""Cache and write-batching behaviour for the calendar (audit P-2, P-4, P-6).

The claims under test:

* a write through the repository is visible on the very next read (the cache is
  invalidated, not merely short-lived);
* a repeated read of an unchanged range does not re-run the expansion;
* two tenants never share an entry;
* the cache itself expires and evicts on schedule.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from helix_codex_app import db
from helix_codex_app.cache import TTLCache
from helix_codex_app.modules.calendar.repository import CalendarRepository


def _month_range() -> tuple[str, str]:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=32)).replace(day=1)
    return start.isoformat(), end.isoformat()


@pytest.fixture()
def repo(tmp_path):
    conn = db.connect(db_path=str(tmp_path / "app.db"))
    db._init_schema(conn)
    yield CalendarRepository(conn)
    conn.close()


def _create(repo: CalendarRepository, *, tenant: str, creator: str, title: str):
    starts = datetime.now(timezone.utc).replace(day=15, hour=9, minute=0, second=0, microsecond=0)
    return repo.create_event(
        tenant_id=tenant,
        domain_id=None,
        title=title,
        kind="meeting",
        starts_at=starts.isoformat(),
        ends_at=(starts + timedelta(hours=1)).isoformat(),
        all_day=False,
        location=None,
        room_id=None,
        creator_account_id=creator,
        recurrence_rule="",
        attendee_account_ids=("guest-1", "guest-2"),
    )


def test_a_write_is_visible_on_the_next_read(repo):
    from_at, to_at = _month_range()
    assert repo.list_events(tenant_id="tenant-a", account_id="owner", from_at=from_at, to_at=to_at) == []
    _create(repo, tenant="tenant-a", creator="owner", title="Planning")
    listed = repo.list_events(tenant_id="tenant-a", account_id="owner", from_at=from_at, to_at=to_at)
    assert [event.title for event in listed] == ["Planning"]


def test_repeated_read_skips_the_expansion(repo, monkeypatch):
    from_at, to_at = _month_range()
    _create(repo, tenant="tenant-a", creator="owner", title="Planning")

    calls = {"n": 0}
    original = CalendarRepository._expand

    def counting(self, event, from_dt, to_dt):
        calls["n"] += 1
        return original(self, event, from_dt, to_dt)

    monkeypatch.setattr(CalendarRepository, "_expand", counting)

    first = repo.list_events(tenant_id="tenant-a", account_id="owner", from_at=from_at, to_at=to_at)
    second = repo.list_events(tenant_id="tenant-a", account_id="owner", from_at=from_at, to_at=to_at)

    assert [event.title for event in first] == [event.title for event in second]
    assert calls["n"] == 1, "the second read should have been served from cache"


def test_tenants_never_share_an_entry(repo):
    from_at, to_at = _month_range()
    _create(repo, tenant="tenant-a", creator="owner", title="Planning")
    tenant_a = repo.list_events(tenant_id="tenant-a", account_id="owner", from_at=from_at, to_at=to_at)
    tenant_b = repo.list_events(tenant_id="tenant-b", account_id="owner", from_at=from_at, to_at=to_at)
    assert len(tenant_a) == 1
    assert tenant_b == []


def test_cancel_invalidates_the_cached_range(repo):
    from_at, to_at = _month_range()
    event = _create(repo, tenant="tenant-a", creator="owner", title="Planning")
    assert len(repo.list_events(tenant_id="tenant-a", account_id="owner", from_at=from_at, to_at=to_at)) == 1
    repo.cancel_event(event.event_id, "tenant-a")
    assert repo.list_events(tenant_id="tenant-a", account_id="owner", from_at=from_at, to_at=to_at) == []


def test_cache_expires_and_evicts():
    now = {"t": 100.0}
    cache = TTLCache(maxsize=2, ttl_seconds=5.0, clock=lambda: now["t"])
    cache.set(("k", 1), "a")
    assert cache.get(("k", 1)) == "a"
    now["t"] += 6.0
    assert cache.get(("k", 1)) is None

    cache.set(("k", 2), "b")
    cache.set(("k", 3), "c")
    cache.set(("k", 4), "d")
    stats = cache.stats()
    assert stats["size"] == 2
    assert stats["evictions"] == 1


def test_invalidate_prefix_only_drops_the_named_tenant():
    cache = TTLCache(ttl_seconds=60.0)
    cache.set(("db", "tenant-a", "x"), 1)
    cache.set(("db", "tenant-b", "x"), 2)
    assert cache.invalidate_prefix(("db", "tenant-a")) == 1
    assert cache.get(("db", "tenant-a", "x")) is None
    assert cache.get(("db", "tenant-b", "x")) == 2
