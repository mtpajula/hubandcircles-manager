"""`.env` reader: skips comments, does not override, empty value counts as missing."""

from manager.settings import env, load_env


def test_load_env(tmp_path, monkeypatch):
    monkeypatch.delenv("HC_TEST_A", raising=False)
    monkeypatch.setenv("HC_TEST_B", "old")
    (tmp_path / ".env").write_text("# comment\nHC_TEST_A = 'value'\nHC_TEST_B=new\nHC_TEST_C=\n")
    load_env(tmp_path / ".env")
    assert env("HC_TEST_A") == "value"
    assert env("HC_TEST_B") == "old"
    assert env("HC_TEST_C", "default") == "default"
