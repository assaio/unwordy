"""Local checks that work even when an agent host does not call a hook."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import extract, lint, profile


def _git(root, *args, check=True):
    return subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=check)


def _root():
    result = _git(Path.cwd(), "rev-parse", "--show-toplevel")
    return Path(os.fsdecode(result.stdout).strip())


def _show(root, revision, path):
    result = _git(root, "show", f"{revision}:{path}", check=False)
    return result.stdout.decode("utf-8", "replace") if result.returncode == 0 else ""


def _changed(root, base=None, staged=False):
    options = ["diff", "--no-ext-diff", "--name-status", "-z", "-M", "--diff-filter=ACMRT"]
    if staged:
        options.append("--cached")
    elif base:
        options.append(base)
    else:
        raise ValueError("choose --diff BASE or --staged")
    fields = iter(_git(root, *options, "--").stdout.split(b"\0"))
    for raw_status in fields:
        if not raw_status:
            break
        status = os.fsdecode(raw_status)
        old_rel = os.fsdecode(next(fields))
        rel = os.fsdecode(next(fields)) if status.startswith(("R", "C")) else old_rel
        path = root / rel
        if staged:
            after = _show(root, "", rel)  # Git's :path index syntax
            before = _show(root, "HEAD", old_rel)
        else:
            try:
                after = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            before = _show(root, base, old_rel)
        change = extract._diff(str(path), before, after)
        if change:
            yield change


def _message(path, surface):
    text = Path(path).read_text(encoding="utf-8", errors="replace").strip("\n")
    title, _, body = text.partition("\n")
    return extract.Message(surface, str(path), title, body.strip("\n"))


def check(args):
    root = _root() if args.diff or args.staged or args.commits else Path.cwd()
    prof = profile.resolve(root)
    if not prof.enabled or os.environ.get("UNWORDY_OFF") == "1":
        findings = []
    else:
        findings = []
        if args.diff or args.staged:
            for change in _changed(root, args.diff, args.staged):
                for finding in lint.lint_change(change, prof.settings, root):
                    finding.target = os.path.relpath(change.path, root)
                    findings.append(finding)
        if args.message_file:
            msg = _message(args.message_file, args.surface)
            for finding in lint.lint_message(msg, prof.settings,
                                             profile.commit_conventions(root)):
                finding.target = str(args.message_file)
                findings.append(finding)
        if args.commits:
            result = _git(root, "log", f"{args.commits}..HEAD",
                          "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e")
            for record in result.stdout.decode("utf-8", "replace").split("\x1e"):
                parts = record.strip().split("\x1f", 5)
                if len(parts) != 6:
                    continue
                title, _, body = parts[5].strip().partition("\n")
                meta = f"author={parts[1]} <{parts[2]}>\ncommitter={parts[3]} <{parts[4]}>"
                msg = extract.Message("commit", parts[0], title, body, meta)
                for finding in lint.lint_message(msg, prof.settings,
                                                 profile.commit_conventions(root)):
                    finding.target = parts[0][:12]
                    findings.append(finding)
    rows = [{"rule": f.rule, "effect": lint.action(f, prof.settings),
             "target": f.target, "reason": f.reason} for f in findings]
    rows = [row for row in rows if row["effect"] != "ignore"]
    if args.json:
        print(json.dumps({"findings": rows}, ensure_ascii=False))
    else:
        for row in rows:
            print(f"{row['target']}: unwordy {row['rule']} ({row['effect']}): {row['reason']}")
    return 1 if any(row["effect"] == "block" or args.fail_on_warn for row in rows) else 0


def doctor(args):
    prof = profile.resolve()
    root = Path(__file__).resolve().parents[1]
    data = {
        "python": sys.version.split()[0],
        "plugin_root": str(root),
        "profile": str(prof.path) if prof.path else "built-in senior",
        "enabled": prof.enabled,
        "strict": prof.settings["strict"],
        "hook_file": (root / "hooks" / "hooks.json").is_file(),
        "host_trust": "check the host hook browser; local CLI cannot inspect it",
    }
    identity = _git(Path.cwd(), "config", "user.name", check=False).stdout.decode("utf-8", "replace").strip()
    data["git_identity"] = (
        "agent-like; check git config user.name" if re.fullmatch(
            r"(?:claude(?: code)?|codex(?: cli)?|cursor(?: agent)?|chatgpt|copilot|gemini)",
            identity, re.I) else "configured" if identity else "not configured"
    )
    if args.json:
        print(json.dumps(data, ensure_ascii=False))
    else:
        for key, value in data.items():
            print(f"{key}: {value}")
    return 0


def examples(args):
    root = _root()
    if args.show:
        for revision in args.show:
            result = _git(root, "show", "-s", "--format=%B", revision)
            print(result.stdout.decode("utf-8", "replace").strip())
            print()
        return 0
    email = _git(root, "config", "user.email", check=False).stdout.decode().strip()
    if not email:
        raise ValueError("set git user.email or pass selected commit IDs with --show")
    result = _git(root, "log", "--no-merges", "-100", "--format=%H%x1f%ae%x1f%s%x1e")
    count = 0
    for record in result.stdout.decode("utf-8", "replace").split("\x1e"):
        parts = record.strip().split("\x1f", 2)
        if len(parts) != 3 or parts[1] != email:
            continue
        print(f"{parts[0][:12]} {parts[2]}")
        count += 1
        if count >= args.limit:
            break
    return 0


def conventions(args):
    root = _root()
    target = (root / args.path).resolve() if args.path else root
    if root not in (target, *target.parents):
        raise ValueError("path must be inside the repository")
    directory = target if target.is_dir() else target.parent
    candidates = ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", ".unwordy.md", ".editorconfig",
                  "pyproject.toml", "package.json", "tsconfig.json", "go.mod",
                  "rustfmt.toml", ".prettierrc", ".prettierrc.json", ".eslintrc",
                  "biome.json", "mypy.ini", "ruff.toml")
    seen = set()
    while root in (directory, *directory.parents):
        for name in candidates:
            path = directory / name
            if path.is_file() and path not in seen:
                print(path.relative_to(root))
                seen.add(path)
        if directory == root:
            break
        directory = directory.parent
    if target.is_file():
        siblings = [p for p in sorted(target.parent.iterdir()) if p.is_file() and
                    p != target and p.suffix == target.suffix][:3]
        for sibling in siblings:
            print(f"nearby: {sibling.relative_to(root)}")
    result = _git(root, "log", "-5", "--format=%s", check=False)
    for subject in result.stdout.decode("utf-8", "replace").splitlines():
        print(f"commit: {subject}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="unwordy")
    sub = parser.add_subparsers(dest="command", required=True)
    checking = sub.add_parser("check", help="check a Git diff or message before review")
    source = checking.add_mutually_exclusive_group()
    source.add_argument("--diff", metavar="BASE", help="compare worktree with a Git revision")
    source.add_argument("--staged", action="store_true", help="check staged changes")
    checking.add_argument("--commits", metavar="BASE", help="check messages and authors in BASE..HEAD")
    checking.add_argument("--message-file", type=Path)
    checking.add_argument("--surface", choices=("commit", "pr", "issue", "comment"))
    checking.add_argument("--json", action="store_true")
    checking.add_argument("--fail-on-warn", action="store_true")
    checking.set_defaults(func=check)
    diagnostics = sub.add_parser("doctor", help="show local profile and hook readiness")
    diagnostics.add_argument("--json", action="store_true")
    diagnostics.set_defaults(func=doctor)
    history = sub.add_parser("examples", help="list or show local commit examples")
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--show", nargs="+", metavar="COMMIT")
    history.set_defaults(func=examples)
    inventory = sub.add_parser("conventions", help="list nearby repo conventions")
    inventory.add_argument("--path", default="")
    inventory.set_defaults(func=conventions)
    args = parser.parse_args(argv)
    if args.command == "check" and not (args.diff or args.staged or args.message_file or args.commits):
        parser.error("check needs --diff BASE, --staged, --commits BASE or --message-file")
    if args.command == "check" and bool(args.message_file) != bool(args.surface):
        parser.error("--message-file and --surface must be used together")
    try:
        return args.func(args)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"unwordy: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
