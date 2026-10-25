from datetime import datetime

import pytest

import config as C
import run


@pytest.fixture
def gh(monkeypatch, tmp_path):
    out = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GH_TOKEN", "t")
    return out


def _due(monkeypatch, gh, hour, sent, force=False):
    monkeypatch.setattr(run, "now_awst", lambda: datetime(2026, 10, 24, hour, 5, tzinfo=C.AWST))
    monkeypatch.setattr(run, "_marker_exists", lambda name, repo, token: sent)
    run.main(["due"] + (["--force"] if force else []))
    return dict(line.split("=", 1) for line in gh.read_text().splitlines())


def test_not_due_before_five(monkeypatch, gh):
    assert _due(monkeypatch, gh, 4, sent=False)["due"] == "no"


def test_due_at_five(monkeypatch, gh):
    assert _due(monkeypatch, gh, 5, sent=False)["due"] == "yes"


def test_due_after_five_until_sent(monkeypatch, gh):
    out = _due(monkeypatch, gh, 9, sent=False)
    assert out == {"due": "yes", "marker": "mobs-sent-2026-10-24"}


def test_not_due_once_sent(monkeypatch, gh):
    assert _due(monkeypatch, gh, 9, sent=True)["due"] == "no"


def test_force_sends_regardless(monkeypatch, gh):
    assert _due(monkeypatch, gh, 3, sent=True, force=True)["due"] == "yes"
