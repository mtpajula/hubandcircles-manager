"""Tool state file: last publish time survives a round trip and a missing file is not an error."""

from datetime import UTC, datetime

from manager.state import last_publish, mark_published


def test_round_trip(tmp_path):
    path = tmp_path / ".state.json"
    assert last_publish(path) is None
    when = mark_published(path, datetime(2026, 9, 12, 10, 0, tzinfo=UTC))
    assert last_publish(path) == when
    (tmp_path / ".state.json").write_text("not json")
    assert last_publish(path) is None
