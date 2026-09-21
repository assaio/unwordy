---
name: sync
description: Render the unwordy voice into AGENTS.md, .cursor/rules/unwordy.mdc and ~/.codex/AGENTS.md and install the Codex and Cursor hook configs. Safe to run twice.
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(ls *) Bash(test *)
---

Put the current voice into the files other tools read. Running this twice
changes nothing.

## 1. Build the block

Run `sh "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" render` and use its output
verbatim as BLOCK. If you cannot run it, assemble BLOCK yourself:

- first line: `<!-- unwordy:start (managed by unwordy; edit .unwordy.md or ~/.config/unwordy/style.md instead) -->`
- then `${CLAUDE_PLUGIN_ROOT}/unwordy/presets/core.md` verbatim
- then a blank line, then the voice body: the body of the profile file when it
  has one, otherwise `${CLAUDE_PLUGIN_ROOT}/unwordy/presets/<preset>.md`
- last line: `<!-- unwordy:end -->`

The profile is `.unwordy.md` from this directory up to the git root, else
`~/.config/unwordy/style.md`, else the `senior` preset.

## 2. Write the project files

- `AGENTS.md`: replace whatever sits between the two markers. With no markers,
  append a blank line and BLOCK. Create the file with BLOCK if it is missing.
- `.cursor/rules/unwordy.mdc`: `---`, `description: unwordy writing style`,
  `alwaysApply: true`, `---`, then BLOCK. Overwrite the whole file.

Read each file first. If it already holds exactly that text, leave it alone
and report it as unchanged.

## 3. Ask before the machine-wide files

Check `test -d ~/.codex` and `test -d ~/.cursor`. List what you would write,
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

Skip the hook files for a tool that already loads unwordy as its own plugin,
or the lints run twice. For Codex, `codex plugin list` shows
`unwordy@unwordy installed, enabled` in that case.

## 4. Report

One line per file: written, updated or unchanged. Then say that Codex and
Cursor pick up new hooks on their next start, and that Codex runs a new hook
only after it is reviewed once in `/hooks`.
