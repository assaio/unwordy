---
name: sync
description: Render the unwordy voice into AGENTS.md, .cursor/rules/unwordy.mdc and ~/.codex/AGENTS.md and install the Codex and Cursor hook configs. Safe to run twice.
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(ls *) Bash(test *) Bash(sh *) Bash(codex plugin list)
---

Put the current voice into the files other tools read. Running this twice
changes nothing.

## 1. Build the block

Use the local CLI's `voice` output when available. Otherwise resolve the first
profile in this order: an existing `$UNWORDY_STYLE`, the nearest `.unwordy.md`
up to the git root, `$XDG_CONFIG_HOME/unwordy/style.md` (default
`~/.config/unwordy/style.md`). Honor enabled, disabled rules, limits, role,
tone and disclosure. With no profile, use clear direct language and retain
facts, uncertainty and evidence. Do not add fixed punctuation or length bans.

Wrap the resolved voice in `<!-- unwordy:start (managed by unwordy; edit
.unwordy.md or ~/.config/unwordy/style.md instead) -->` and
`<!-- unwordy:end -->`. A disabled profile removes an existing managed block.

## 2. Write the project files

- `AGENTS.md`: replace whatever sits between the two markers. With no markers,
  append a blank line and BLOCK. Create the file with BLOCK if it is missing.
- `.cursor/rules/unwordy.mdc`: `---`, `description: unwordy writing style`,
  `alwaysApply: true`, `---`, then BLOCK. Replace only this managed file. Preserve unrelated rules in other files.

Read each file first. If it already holds exactly that text, leave it alone
and report it as unchanged.

## 3. Ask before the machine-wide files

Check for existing Codex and Cursor configuration directories. List what you would write,
then ask once before writing anything under the home directory:

- `~/.codex/AGENTS.md`: the same marker block.
- `~/.codex/hooks.json`: the entries from
  `${CLAUDE_PLUGIN_ROOT}/hooks/codex.hooks.json` with `${CLAUDE_PLUGIN_ROOT}`
  replaced by the real plugin path. Merge into the file's `hooks` object, keep
  every other hook, and skip entries whose command already mentions unwordy.
- `~/.cursor/hooks.json`: the entries from
  `${CLAUDE_PLUGIN_ROOT}/hooks/cursor.hooks.json` with `${CURSOR_PLUGIN_ROOT}`
  replaced by the real plugin path, merged into the matching arrays under
  `hooks`, keeping `"version": 1`.

If this is a skills-only installation, sync the voice only; hook assets are
not installed. Locate the plugin root before using hook templates.
Skip the hook files for a tool that already loads unwordy as its own plugin,
or the lints run twice. For Codex, `codex plugin list` shows
`unwordy@unwordy installed, enabled` in that case.

## 4. Report

One line per file: written, updated or unchanged. Then say that Codex and
Cursor pick up new hooks on their next start, and that Codex runs a new hook
only after it is reviewed once in `/hooks`.
