"""Hook entry point: JSON on stdin, decision JSON on stdout, exit 0 whatever happens."""

import json
import os
import sys
import traceback
from datetime import datetime

from . import extract, lint, profile, render, state


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    mode = argv[0] if argv else ""
    try:
        if mode == "render":
            out = _render(argv[1:])
        else:
            out = run(mode, _load(sys.stdin.buffer.read().decode("utf-8", "replace")))
        if out:
            text = out if isinstance(out, str) else json.dumps(out)
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.flush()
    except Exception:
        _log(mode)
    return 0


def run(mode, payload):
    """Decision for one hook event, or None when there is nothing to say."""
    handler = _HANDLERS.get(mode)
    if handler is None or _off():
        return None
    payload = normalize(payload)
    prof = profile.resolve(_cwd(payload))
    if not prof.enabled:
        return None
    return handler(payload, prof, _cwd(payload))


def _cwd(payload):
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        return cwd
    roots = payload.get("workspace_roots")
    if isinstance(roots, list) and roots and isinstance(roots[0], str) and roots[0]:
        return roots[0]
    return os.getcwd()


def normalize(payload):
    """Map Cursor's native payloads onto the Claude Code shape; Codex already matches."""
    event = payload.get("hook_event_name")
    if event == "beforeShellExecution":
        return dict(payload, tool_name="Bash", tool_input={"command": payload.get("command") or ""},
                    host="cursor")
    if event == "sessionStart":
        return dict(payload, hook_event_name="SessionStart", host="cursor")
    if event == "beforeMCPExecution":
        return dict(payload, host="cursor")
    if event == "preToolUse" and payload.get("tool_name") == "Write":
        return dict(payload, host="cursor")
    if payload.get("tool_name") == "Shell":
        tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
        return dict(payload, tool_name="Bash", tool_input={"command": tool_input.get("command") or ""},
                    host="cursor")
    return payload


def _session_start(payload, prof, cwd):
    try:
        state.prune()
    except OSError:
        pass
    source = _display(prof.path) if prof.path else "built-in default"
    header = f"Writing style the user set with unwordy (preset {prof.settings['preset']}, {source}):"
    context = f"{header}\n\n{prof.voice()}"
    if payload.get("host") == "cursor":
        return {"additional_context": context}
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}


def _pre_edit(payload, prof, cwd):
    changes = extract.edit_changes(payload.get("tool_name"), payload.get("tool_input"), cwd, _want(prof, cwd))
    return _decide(_lint_changes(changes, prof, cwd), prof, payload)


def _pre_bash(payload, prof, cwd):
    tool_input = payload.get("tool_input")
    command = str((tool_input.get("command") if isinstance(tool_input, dict) else None) or "")
    findings, conventions = [], None
    for message in extract.shell_messages(command, cwd):
        if conventions is None:
            conventions = profile.commit_conventions(cwd)
        for finding in lint.lint_message(message, prof.settings, conventions):
            finding.target = f"bash:{message.target}"
            findings.append(finding)
    findings += _lint_changes(extract.shell_writes(command, cwd, _want(prof, cwd)), prof, cwd)
    return _decide(findings, prof, payload)


def _want(prof, cwd):
    def want(path):
        return extract.syntax_for(path) is not None and not lint.exempt_path(path, prof.settings, cwd)
    return want


def _lint_changes(changes, prof, cwd):
    findings = []
    for change in changes:
        for finding in lint.lint_change(change, prof.settings, cwd):
            finding.target = change.path
            findings.append(finding)
    return findings


def _pre_mcp(payload, prof, cwd):
    tool = str(payload.get("tool_name") or "")
    findings = []
    for key, text in extract.mcp_fields(payload.get("tool_input")):
        for finding in lint.lint_field(key, text, prof.settings):
            finding.target = f"{tool}:{key}"
            findings.append(finding)
    return _decide(findings, prof, payload)


def _stop(payload, prof, cwd):
    if prof.settings["strict"] != "block" or payload.get("stop_hook_active"):
        return None
    question, transcript_reply = extract.read_transcript_tail(payload.get("transcript_path") or "")
    reply = payload.get("last_assistant_message")
    reply = reply if isinstance(reply, str) and reply.strip() else transcript_reply
    findings = [f for f in lint.lint_reply(reply, question, prof.settings) if not f.disabled(prof.settings)]
    if not findings:
        return None
    return {"decision": "block", "reason": "\n".join(str(f) for f in findings)}


def _decide(findings, prof, payload):
    settings = prof.settings
    deny, warn = [], []
    for finding in findings:
        effect = lint.action(finding, settings)
        if effect == "warn":
            warn.append(finding)
        elif effect == "block":
            deny.append(finding)
    blocked = []
    if deny:
        guard = state.Guard(payload.get("session_id") or payload.get("conversation_id"))
        for finding in deny:
            if not finding.hard and guard.exhausted(finding.family, finding.target):
                finding.reason += " Passed as a warning after two denials."
                warn.append(finding)
            else:
                blocked.append(finding)
        if blocked:
            try:
                guard.record((f.family, f.target) for f in blocked)
            except OSError:
                pass
    cursor = payload.get("host") == "cursor"
    if blocked:
        reason = "\n".join(str(f) for f in blocked + warn)
        if cursor:
            return {"permission": "deny", "user_message": reason, "agent_message": reason}
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": reason}}
    if warn and not cursor:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "additionalContext": "\n".join(str(f) for f in warn)}}
    return None


def _render(args):
    voice = profile.resolve(os.getcwd()).voice()
    return render.mdc(voice) if args[:1] == ["mdc"] else render.block(voice) + "\n"


def _load(raw):
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _off():
    return os.environ.get("UNWORDY_OFF", "").strip().lower() not in ("", "0", "false", "no")


def _display(path):
    home = os.path.expanduser("~")
    text = str(path)
    return "~" + text[len(home):] if home not in ("", "/") and text.startswith(home + os.sep) else text


def _log(mode):
    try:
        path = state.data_dir() / "unwordy.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 1_000_000:
            path.unlink()
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {mode}\n{traceback.format_exc()}\n")
    except Exception:
        pass


_HANDLERS = {
    "session-start": _session_start,
    "pre-edit": _pre_edit,
    "pre-bash": _pre_bash,
    "pre-mcp": _pre_mcp,
    "stop": _stop,
}


if __name__ == "__main__":
    sys.exit(main())
