from datetime import UTC, datetime, timedelta

from app.bot.client import check_due


def test_restart_skips_checks_that_are_not_due():
    current = datetime(2026, 8, 21, 18, 0, tzinfo=UTC)
    checked = (current - timedelta(minutes=1)).isoformat()

    assert check_due(checked, 120, current=current) is False
    assert check_due(checked, 30, current=current) is True
