import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def call(repo, *args):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "unwordy", *args], cwd=repo,
                          env=env, text=True, capture_output=True)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test Person")
    git(repo, "config", "user.email", "test@example.com")
    (repo / "a.py").write_text("def answer():\n    return 1\n")
    git(repo, "add", "a.py")
    git(repo, "commit", "-qm", "Add answer")
    return repo


def test_check_diff_and_staged_use_the_same_rule(tmp_path):
    repo = repository(tmp_path)
    (repo / "a.py").write_text("# This function returns the answer\ndef answer():\n    return 1\n")
    worktree = call(repo, "check", "--diff", "HEAD", "--json")
    assert worktree.returncode == 1
    assert json.loads(worktree.stdout)["findings"][0]["rule"] == "H4a"
    git(repo, "add", "a.py")
    staged = call(repo, "check", "--staged", "--json")
    assert staged.returncode == 1
    assert json.loads(staged.stdout)["findings"] == json.loads(worktree.stdout)["findings"]


def test_check_message_and_profile_policy(tmp_path):
    repo = repository(tmp_path)
    message = repo / "message.txt"
    message.write_text("Fix retry\n\nCo-Authored-By: Claude\n")
    assert call(repo, "check", "--message-file", str(message), "--surface", "commit").returncode == 1
    (repo / ".unwordy.md").write_text("---\ncommit.attribution: allow\n---\n")
    assert call(repo, "check", "--message-file", str(message), "--surface", "commit").returncode == 0


def test_examples_list_before_showing_content(tmp_path):
    repo = repository(tmp_path)
    listing = call(repo, "examples")
    assert listing.returncode == 0
    assert "Add answer" in listing.stdout
    assert "test@example.com" not in listing.stdout
    revision = listing.stdout.split()[0]
    shown = call(repo, "examples", "--show", revision)
    assert shown.returncode == 0
    assert shown.stdout.strip() == "Add answer"


def test_doctor_and_conventions_are_read_only(tmp_path):
    repo = repository(tmp_path)
    (repo / "AGENTS.md").write_text("Follow the team style.\n")
    doctor = call(repo, "doctor", "--json")
    assert doctor.returncode == 0
    assert json.loads(doctor.stdout)["hook_file"] is True
    inventory = call(repo, "conventions", "--path", "a.py")
    assert inventory.returncode == 0
    assert "AGENTS.md" in inventory.stdout
    assert "commit: Add answer" in inventory.stdout


def test_check_commits_catches_agent_author(tmp_path):
    repo = repository(tmp_path)
    git(repo, "commit", "--allow-empty", "--author=Claude <claude@example.com>", "-qm", "Fix retry")
    result = call(repo, "check", "--commits", "HEAD~1", "--json")
    assert result.returncode == 1
    rows = json.loads(result.stdout)["findings"]
    assert any(row["rule"] == "H1" for row in rows)


def test_rename_only_does_not_recheck_unchanged_comments(tmp_path):
    repo = repository(tmp_path)
    (repo / "a.py").write_text("# This function returns the answer\ndef answer():\n    return 1\n")
    git(repo, "add", "a.py")
    git(repo, "commit", "-qm", "Add existing comment")
    git(repo, "mv", "a.py", "b.py")
    result = call(repo, "check", "--staged", "--json")
    assert result.returncode == 0
    assert json.loads(result.stdout)["findings"] == []
