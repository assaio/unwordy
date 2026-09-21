"""Style profile: resolution order, flat frontmatter parser, presets."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PRESETS_DIR = Path(__file__).resolve().parent / "presets"
PRESETS = ("lazy", "senior", "qa", "lead", "formal")
DEFAULT_PRESET = "senior"
PROJECT_FILE = ".unwordy.md"

BANNED_EN = (
    "delve", "delving", "leverage", "leveraging", "seamless", "seamlessly",
    "robust", "comprehensive", "streamline", "streamlined", "utilize",
    "utilizing", "facilitate", "tapestry", "testament", "meticulous",
    "meticulously", "pivotal", "paramount", "holistic", "synergy",
    "cutting-edge", "game-changer", "it's worth noting",
)

BANNED_PL = (
    "kompleksowy", "kompleksowe", "kompleksowa", "kompleksowo",
    "holistyczny", "holistyczne", "synergia", "bezproblemowo",
    "innowacyjny", "innowacyjne", "warto zauważyć", "warto podkreślić",
    "podsumowując", "zagłębić się",
)

BANNED_DE = (
    "nahtlos", "nahtlose", "umfassend", "umfassende", "ganzheitlich",
    "ganzheitliche", "innovativ", "innovative", "synergie", "synergien",
    "zukunftssicher", "maßgeschneidert", "leistungsstark",
    "es ist erwähnenswert", "zusammenfassend", "eintauchen",
)

DEFAULTS = {
    "enabled": True,
    "preset": DEFAULT_PRESET,
    "strict": "warn",
    "language": "auto",
    "banned_words": list(BANNED_EN + BANNED_PL + BANNED_DE),
    "allow_ticket_refs": False,
    "max_subject": 72,
    "max_pr_body_lines": 12,
    "max_bullets": 6,
    "ignore": [],
    "disable": [],
}

_LISTS = {"banned_words", "ignore", "disable"}
_INTS = {"max_subject", "max_pr_body_lines", "max_body_lines", "max_bullets"}
_BOOLS = {"enabled", "allow_ticket_refs"}
_TRUE = {"true", "yes", "on", "1"}
_FALSE = {"false", "no", "off", "0"}
_STRICT = ("warn", "block", "off")


@dataclass
class Profile:
    settings: dict
    body: str
    path: Optional[Path] = None

    @property
    def enabled(self):
        return bool(self.settings["enabled"])

    def voice(self):
        """Core rules plus the preset or custom body, as injected at session start."""
        parts = [core_rules(), self.body]
        language = str(self.settings.get("language") or "auto").strip()
        if language.lower() != "auto":
            parts.append(f"Default language for replies and tracker text: {language}.")
        return "\n\n".join(p for p in parts if p)


def parse(text):
    """Split profile text into (settings, body). Values are typed by key."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text.strip()
    settings = {}
    for line in lines[1:end]:
        key, sep, raw = line.partition(":")
        key = key.strip().lower().replace("-", "_")
        if not sep or not key or key.startswith("#") or not key.replace("_", "").replace(".", "").isalnum():
            continue
        value = _coerce(key.rsplit(".", 1)[-1], _strip_comment(raw))
        if value is not None:
            settings[key] = value
    return settings, "\n".join(lines[end + 1:]).strip()


def _strip_comment(raw):
    for i, ch in enumerate(raw):
        if ch == "#" and (i == 0 or raw[i - 1] in " \t"):
            return raw[:i].strip()
    return raw.strip()


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _coerce(key, raw):
    value = _unquote(raw.strip())
    if key in _LISTS:
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
        return [_unquote(item.strip()) for item in value.split(",") if item.strip()]
    if key in _INTS:
        try:
            return int(value)
        except ValueError:
            return None
    if key in _BOOLS:
        low = value.lower()
        return True if low in _TRUE else False if low in _FALSE else None
    return value


def find(cwd, env=None):
    """Return the first profile path in resolution order, or None."""
    env = os.environ if env is None else env
    override = env.get("UNWORDY_STYLE")
    if override:
        path = Path(override).expanduser()
        if path.is_file():
            return path
    here = Path(cwd).expanduser().resolve()
    for directory in (here, *here.parents):
        candidate = directory / PROJECT_FILE
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    config_home = env.get("XDG_CONFIG_HOME") or os.path.join(
        env.get("HOME") or os.path.expanduser("~"), ".config"
    )
    candidate = Path(config_home) / "unwordy" / "style.md"
    return candidate if candidate.is_file() else None


def resolve(cwd=None, env=None):
    env = os.environ if env is None else env
    path = find(cwd or os.getcwd(), env)
    raw, body = {}, ""
    if path is not None:
        try:
            raw, body = parse(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            path = None
    settings = dict(DEFAULTS)
    settings.update(raw)
    settings["preset"] = str(settings["preset"]).strip().lower()
    settings["strict"] = str(settings["strict"]).strip().lower()
    if settings["strict"] not in _STRICT:
        settings["strict"] = DEFAULTS["strict"]
    settings["disable"] = [rule_id(rule) for rule in settings["disable"]]
    return Profile(settings, body or preset_body(settings["preset"]), path)


def rule_id(text):
    """Normalise a rule id from the profile: h2 -> H2, s5F -> S5f."""
    text = str(text).strip()
    return text[:2].upper() + text[2:].lower()


_CONVENTION_FILES = ("commitlint.config.", ".commitlintrc", ".gitmessage")
_TEMPLATE_KEY = re.compile(r"^\s*template\s*=", re.M)
_COMMIT_SECTION = re.compile(r"^\s*\[commit\]\s*$(.*?)(?=^\s*\[|\Z)", re.M | re.S)


def commit_conventions(cwd, env=None):
    """True when commitlint or a commit template already governs commit messages here."""
    env = os.environ if env is None else env
    home = Path(env.get("HOME") or os.path.expanduser("~"))
    root = _git_root(cwd)
    for directory in {root, home}:
        try:
            names = os.listdir(directory)
        except OSError:
            continue
        if any(name.startswith(_CONVENTION_FILES) for name in names):
            return True
    if root is not None and "commitlint" in _read(root / "package.json"):
        return True
    for config in (root / ".git" / "config" if root else None, home / ".gitconfig"):
        if config is None:
            continue
        section = _COMMIT_SECTION.search(_read(config))
        if section and _TEMPLATE_KEY.search(section.group(1)):
            return True
    return False


def _git_root(cwd):
    here = Path(cwd).expanduser().resolve()
    return next((d for d in (here, *here.parents) if (d / ".git").exists()), None)


def _read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def preset_body(name):
    return _read_preset(name if name in PRESETS else DEFAULT_PRESET)


def core_rules():
    return _read_preset("core")


def _read_preset(name):
    return (PRESETS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
