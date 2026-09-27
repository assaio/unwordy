"""Style profile: resolution order, flat frontmatter parser, presets."""

import os
import re
from dataclasses import dataclass, field
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
    "attribution": "block",
    "max_subject": 72,
    "max_pr_body_lines": 12,
    "max_bullets": 6,
    "ignore": [],
    "disable": [],
    "role": "auto",
    "tone": "auto",
    "pr_template": "auto",
}

_LISTS = {"banned_words", "ignore", "disable"}
_INTS = {"max_subject", "max_pr_body_lines", "max_body_lines", "max_bullets"}
_BOOLS = {"enabled", "allow_ticket_refs"}
_TRUE = {"true", "yes", "on", "1"}
_FALSE = {"false", "no", "off", "0"}
_STRICT = ("warn", "block", "off")
SURFACES = ("commit", "pr", "issue", "comment", "code", "docs", "reply")
RULE_IDS = frozenset(("H1", "H2", "H3", "H4", "S1", "S2", "S3", "S4", "S5", "S6", "S7",
                     "H2a", "H2b", "H2c", "H2d", "H4a", "H4b", "S5a", "S5b", "S5c", "S5d",
                     "S5e", "S5f", "S6a", "S6b", "S6c", "S7a", "S7b"))
_ENUMS = {"strict": _STRICT, "preset": (*PRESETS, "custom"),
          "role": ("auto", "developer", "qa", "design", "lead"),
          "tone": ("auto", "neutral", "direct", "warm", "formal"),
          "pr_template": ("auto", "respect", "ignore")}
_ROLES = {
    "developer": "PRs and reviews: retain the reason, risk, evidence and relevant code location.",
    "qa": "Bug reports: retain steps, expected and actual results, versions, environment and frequency. Keep exact errors and useful descriptive terms.",
    "design": "Design reviews and handoffs: retain UI states, behavior, rationale, accessibility requirements and implementation constraints.",
    "lead": "Decisions: retain the decision, trade-off, owner and next step when provided.",
}
_TONES = {"neutral": "Use a neutral conversational register.", "direct": "Be direct; keep enough context for the reader.",
          "warm": "Be warm; keep useful acknowledgements and the writer's personality.",
          "formal": "Use complete sentences and a formal register."}


@dataclass
class Profile:
    settings: dict
    body: str
    path: Optional[Path] = None
    diagnostics: list = field(default_factory=list)

    @property
    def enabled(self):
        return bool(self.settings["enabled"])

    def voice(self):
        """Core rules plus the preset or custom body, as injected at session start."""
        if not self.enabled:
            return ""
        body = self.body
        if self.settings["tone"] != "auto" and body == preset_body(self.settings["preset"]):
            body = ""
        parts = [core_rules(), body]
        role = self.settings["role"]
        if role == "auto":
            role = {"qa": "qa", "lead": "lead"}.get(self.settings["preset"], "developer")
        parts.append(_ROLES[role])
        if self.settings["tone"] in _TONES:
            parts.append(_TONES[self.settings["tone"]])
        parts.extend(self._constraints())
        language = str(self.settings.get("language") or "auto").strip()
        if language.lower() != "auto":
            parts.append(f"Default language for replies and tracker text: {language}.")
        return "\n\n".join(p for p in parts if p)

    def _constraints(self):
        from . import lint

        settings = self.settings
        active = lambda rule: lint.action(lint.Finding(rule, ""), settings) != "ignore"
        lines = []
        if active("S1"):
            lines.append("Prefer commas, colons or full stops to em dashes.")
        if active("S2") and settings["banned_words"]:
            lines.append("Avoid filler from the configured word list: " + ", ".join(settings["banned_words"]) + ". Preserve exact quotes and technical identifiers.")
        if active("H2d") and not settings["allow_ticket_refs"]:
            lines.append("Flag ticket references in code comments for review; keep a useful workaround reference when the repository needs it.")
        if active("H4a") or active("H4b"):
            lines.append("Review comments that restate code; retain public API contracts and non-obvious constraints.")
        if active("S5a") or active("S5b") or active("S5c"):
            limits = []
            for surface in ("commit", "pr", "issue", "comment"):
                values = []
                if active("S5a"):
                    values.append(f"subject {lint._limit(settings, surface, 'max_subject', 72)} characters")
                if active("S5b"):
                    values.append(f"body {lint._limit(settings, surface, 'max_body_lines', 12)} nonblank prose lines")
                if active("S5c"):
                    values.append(f"bullets {lint._limit(settings, surface, 'max_bullets', 6)}")
                limits.append(surface + ": " + ", ".join(values))
            lines.append("Preferred limits, subject to required repository content: " + "; ".join(limits) + ".")
        if active("S6a"):
            lines.append("Use the required PR template. Omit unused scaffolding when no template requires it.")
        if "H1" not in settings["disable"] and settings.get("rule.h1") != "off":
            attribution = [f"{key} {value}" for key, value in settings.items()
                           if key == "attribution" or key.endswith(".attribution")]
            lines.append("Attribution policy: " + "; ".join(attribution) + ". Required repository disclosure wins.")
        return lines


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
    diagnostics = validate(_read(path)) if path else []
    settings = dict(DEFAULTS)
    for key, value in raw.items():
        if _setting_error(key, value) is None:
            settings[key] = value.lower() if key in _ENUMS or key.endswith(".attribution") or key == "attribution" or key.startswith("rule.") else value
    settings["disable"] = [rule_id(rule) for rule in settings["disable"]]
    return Profile(settings, body or preset_body(settings["preset"]), path, diagnostics)


def _setting_error(key, value):
    base = key.rsplit(".", 1)[-1]
    if key.startswith("rule."):
        if rule_id(base) not in RULE_IDS:
            return "unknown rule id"
        return None if str(value).lower() in _STRICT else "expected warn, block or off"
    if "." in key and (key.split(".")[0] not in SURFACES or base not in ("attribution", "max_subject", "max_body_lines", "max_bullets")):
        return "unknown surface setting"
    if "." not in key and key not in DEFAULTS:
        return "unknown setting"
    if key in _ENUMS and str(value).lower() not in _ENUMS[key]:
        return "expected " + ", ".join(_ENUMS[key])
    if base == "attribution" and str(value).lower() not in ("block", "warn", "allow"):
        return "expected block, warn or allow"
    if base in _INTS and (not isinstance(value, int) or value <= 0):
        return "expected a positive integer"
    if base in _BOOLS and not isinstance(value, bool):
        return "expected true or false"
    if key == "disable" and any(rule_id(item) not in RULE_IDS for item in value):
        return "unknown rule id in disable"
    return None


def validate(text):
    """Diagnose each frontmatter entry, including values parse() cannot coerce."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return ["frontmatter: missing closing ---"]
    problems, seen = [], set()
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, raw = line.partition(":")
        key = key.strip().lower().replace("-", "_")
        value = _coerce(key.rsplit(".", 1)[-1], _strip_comment(raw))
        error = _setting_error(key, value) if sep else "expected key: value"
        if key in seen:
            problems.append(f"{key}: duplicate setting")
        seen.add(key)
        if error:
            problems.append(f"{key}: {error}")
    return problems


def pr_headings(cwd, settings):
    """Headings required by one of the repository's PR or merge request templates."""
    if settings["pr_template"] == "ignore":
        return set()
    root = _git_root(cwd)
    if root is None:
        return set()
    paths = []
    for directory in (root, root / ".github", root / "docs"):
        for name in ("pull_request_template.md", "PULL_REQUEST_TEMPLATE.md"):
            paths.append(directory / name)
        for name in ("PULL_REQUEST_TEMPLATE", "pull_request_template"):
            paths.extend((directory / name).glob("*.md"))
    paths.extend((root / ".gitlab" / "merge_request_templates").glob("*.md"))
    return {line.strip().lower() for path in paths for line in _read(path).splitlines()
            if re.match(r"^\s{0,3}#{1,6}\s+", line)}


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
    for directory in {root, home} - {None}:
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
