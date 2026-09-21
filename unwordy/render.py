"""Marker-delimited voice blocks for AGENTS.md, ~/.codex/AGENTS.md and .cursor/rules/unwordy.mdc."""

import re

START = "<!-- unwordy:start (managed by unwordy; edit .unwordy.md or ~/.config/unwordy/style.md instead) -->"
END = "<!-- unwordy:end -->"
_BLOCK = re.compile(r"<!-- unwordy:start\b[^\n]*?-->.*?<!-- unwordy:end -->", re.S)


def block(voice):
    return f"{START}\n{voice.strip()}\n{END}"


def upsert(text, voice):
    """Replace the managed block in text, or append one. Applying it twice changes nothing."""
    new = block(voice)
    if _BLOCK.search(text):
        return _BLOCK.sub(lambda _: new, text, count=1)
    if not text.strip():
        return new + "\n"
    return text.rstrip("\n") + "\n\n" + new + "\n"


def remove(text):
    stripped = _BLOCK.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", stripped).strip("\n") + "\n" if stripped.strip() else ""


def mdc(voice):
    return (
        "---\n"
        "description: unwordy writing style\n"
        "alwaysApply: true\n"
        "---\n"
        f"{block(voice)}\n"
    )
