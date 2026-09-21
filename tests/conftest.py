import pytest

from unwordy import profile

FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures"
TEMPLATES = FIXTURES.parent.parent / "templates"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Keep every test away from the real home directory and plugin data."""
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "data"))
    monkeypatch.delenv("UNWORDY_STYLE", raising=False)
    monkeypatch.delenv("UNWORDY_OFF", raising=False)
    return home


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "project"
    (path / ".git").mkdir(parents=True)
    return path


@pytest.fixture
def settings():
    return dict(profile.DEFAULTS)
