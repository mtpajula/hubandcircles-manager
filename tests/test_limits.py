"""Target limits are read from limits.json; exceeding one names the limit and the largest file."""

import json
from pathlib import Path

from manager.models import Target
from manager.publish import limits
from manager.publish.bundle import Bundle

BUNDLE = Bundle(Path("/x"), file_count=3, total_bytes=3000, largest=("data/big.pmtiles", 2000))


def test_file_limit_exceeded(tmp_path, monkeypatch):
    strict = tmp_path / "limits.json"
    strict.write_text(json.dumps({"cloudflare-pages": {"max_files": 2}}))
    monkeypatch.setattr(limits, "LIMITS_PATH", strict)
    findings = limits.check_limits(BUNDLE, Target(id="primary", type="cloudflare-pages"))
    assert len(findings) == 1 and findings[0].level == "error"
    assert "files 3" in findings[0].message and "limit 2" in findings[0].message
    assert "data/big.pmtiles" in findings[0].message


def test_directory_has_no_limits():
    assert limits.check_limits(BUNDLE, Target(id="k", type="directory", path="/tmp/x")) == []


def test_real_limits_file_covers_all_types():
    assert set(limits.read_limits()) == set(Target.model_fields["type"].annotation.__args__)
    assert limits.check_limits(BUNDLE, Target(id="primary", type="cloudflare-pages")) == []
