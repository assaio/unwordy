"""Loop guard for soft rules blocked under strict mode."""

import json
import os
import re
import time
from pathlib import Path

LIMIT = 2
MAX_AGE_SECONDS = 7 * 24 * 3600


def data_dir(env=None):
    env = os.environ if env is None else env
    base = env.get("CLAUDE_PLUGIN_DATA")
    if base:
        return Path(base)
    return Path(env.get("HOME") or os.path.expanduser("~")) / ".cache" / "unwordy"


class Guard:
    def __init__(self, session_id, env=None):
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", str(session_id or "default"))[:100] or "default"
        self.path = data_dir(env) / "state" / f"{name}.json"
        self.denials = self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return {str(k): int(v) for k, v in data.get("denials", {}).items()}
        except (OSError, ValueError, AttributeError, TypeError):
            return {}

    @staticmethod
    def _key(rule, target):
        return f"{rule} {target}"

    def exhausted(self, rule, target):
        return self.denials.get(self._key(rule, target), 0) >= LIMIT

    def record(self, pairs):
        for rule, target in pairs:
            key = self._key(rule, target)
            self.denials[key] = self.denials.get(key, 0) + 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"denials": self.denials}), encoding="utf-8")
        os.replace(tmp, self.path)


def prune(env=None, max_age=MAX_AGE_SECONDS, now=None):
    now = time.time() if now is None else now
    for path in (data_dir(env) / "state").glob("*.json"):
        try:
            if now - path.stat().st_mtime > max_age:
                path.unlink()
        except OSError:
            pass
