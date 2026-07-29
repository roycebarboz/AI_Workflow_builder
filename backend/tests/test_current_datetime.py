from datetime import datetime, timezone

from app.tools.current_datetime import get_current_datetime


def test_returns_iso_utc_timestamp():
    before = datetime.now(timezone.utc)
    result = datetime.fromisoformat(get_current_datetime())
    after = datetime.now(timezone.utc)

    assert result.tzinfo is not None
    assert before <= result <= after
