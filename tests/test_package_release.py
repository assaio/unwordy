import hashlib
import importlib.util
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_release", ROOT / "scripts/package_release.py")
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


@pytest.fixture
def release_repo(tmp_path, monkeypatch):
    repo = tmp_path / "release-repo"
    repo.mkdir()
    for name in ("plugin.json", ".codex-plugin/plugin.json", "LICENSE", "docs/assets/unwordy.svg",
                 "skills/unwordy/SKILL.md", "skills/unwordy/agents/openai.yaml", "bin/unwordy", "hooks/hooks.json"):
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    (repo / "bin/unwordy").chmod(0o755)
    (repo / ".gitignore").write_text(".env\n.venv/\n")
    monkeypatch.setattr(package, "ROOT", repo)
    package.git("init", "-q")
    package.git("config", "user.name", "Test Person")
    package.git("config", "user.email", "test@example.com")
    package.git("add", ".")
    package.git("commit", "-qm", "Prepare release")
    monkeypatch.setattr(sys, "argv", ["package_release.py", str(tmp_path / "artifacts")])
    return repo


def test_release_archives_keep_permissions_and_exclude_local_state(release_repo, tmp_path):
    (release_repo / ".env").write_text("LOCAL_ONLY=private\n")
    package.main()
    version = json.loads((release_repo / "plugin.json").read_text())["version"]
    artifacts = tmp_path / "artifacts"
    assert {path.name for path in artifacts.iterdir()} == {
        f"unwordy-{version}.zip", f"unwordy-skill-{version}.zip", "SHA256SUMS",
    }
    with zipfile.ZipFile(artifacts / f"unwordy-{version}.zip") as archive:
        assert "hooks/hooks.json" in archive.namelist()
        assert not any(name.startswith(".git/") or name == ".env" for name in archive.namelist())
        assert archive.getinfo("bin/unwordy").external_attr >> 16 & 0o111 == 0o111
    with zipfile.ZipFile(artifacts / f"unwordy-skill-{version}.zip") as archive:
        assert set(archive.namelist()) == {"unwordy/SKILL.md", "unwordy/agents/openai.yaml"}
    checksums = (artifacts / "SHA256SUMS").read_text().splitlines()
    assert len(checksums) == 2
    for line in checksums:
        digest, name = line.split("  ")
        assert hashlib.sha256((artifacts / name).read_bytes()).hexdigest() == digest


def test_packaging_rejects_uncommitted_content(release_repo, tmp_path):
    (release_repo / "LICENSE").write_text("Uncommitted content\n")
    with pytest.raises(ValueError, match="commit the release"):
        package.main()
    assert not (tmp_path / "artifacts").exists()
