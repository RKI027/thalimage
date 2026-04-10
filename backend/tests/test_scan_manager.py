"""Tests for scan manager."""

import asyncio

from thalimage.services.scan_manager import ScanManager


def test_initial_state():
    mgr = ScanManager()
    assert not mgr.is_running(1)
    assert mgr.get_progress(1) is None


def test_start_scan():
    mgr = ScanManager()
    p = mgr.start(1)
    assert p.phase == "discovering"
    assert p.source_id == 1
    assert mgr.is_running(1)


def test_cannot_start_same_source_twice():
    mgr = ScanManager()
    mgr.start(1)
    assert not mgr.can_start(1)


def test_concurrent_sources_allowed():
    mgr = ScanManager(concurrent=True)
    mgr.start(1)
    assert mgr.can_start(2)


def test_non_concurrent_blocks_other_sources():
    mgr = ScanManager(concurrent=False)
    mgr.start(1)
    assert not mgr.can_start(2)


def test_update_progress():
    mgr = ScanManager()
    mgr.start(1)
    mgr.update(1, phase="processing", current=5, total=10, added=3)
    p = mgr.get_progress(1)
    assert p is not None
    assert p.phase == "processing"
    assert p.current == 5
    assert p.total == 10
    assert p.added == 3


def test_complete_sets_phase():
    mgr = ScanManager()
    mgr.start(1)
    mgr.complete(1, added=10, skipped=5)
    p = mgr.get_progress(1)
    assert p is not None
    assert p.phase == "complete"
    assert not mgr.is_running(1)


def test_fail_sets_error():
    mgr = ScanManager()
    mgr.start(1)
    mgr.fail(1, message="disk full")
    p = mgr.get_progress(1)
    assert p is not None
    assert p.phase == "error"
    assert p.message == "disk full"
    assert not mgr.is_running(1)


async def test_wait_for_update():
    mgr = ScanManager()
    mgr.start(1)

    async def do_update():
        await asyncio.sleep(0.05)
        mgr.update(1, phase="processing", current=3, total=10)

    asyncio.create_task(do_update())
    p = await mgr.wait_for_update(1, timeout=1.0)
    assert p is not None
    assert p.current == 3


async def test_wait_for_update_timeout():
    mgr = ScanManager()
    mgr.start(1)
    p = await mgr.wait_for_update(1, timeout=0.05)
    assert p is not None
    assert p.phase == "discovering"


def test_can_start_after_complete():
    mgr = ScanManager()
    mgr.start(1)
    mgr.complete(1)
    assert mgr.can_start(1)
