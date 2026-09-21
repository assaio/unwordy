# Changelog

## v0.2.2

- Codex loads no lifecycle hook at all until `features.hooks` is true in
  `~/.codex/config.toml`, and it skips a plugin's hooks until `/hooks` trusts
  them once. The README claimed only the second. Both are now in the Codex
  section, next to what four live `codex exec` runs actually did: no hook
  fired in any of them, including with `--dangerously-bypass-hook-trust`.
- The README opens with the problem rather than the feature list, and the
  Codex section no longer promises behaviour nobody has observed.

- Claude Code loads `hooks/hooks.json` on its own, and the plugin manifest
  named it a second time. The hook load failed on install and every rule went
  silent, while the plugin still reported three hooks. The manifest no longer
  declares the file. `claude plugin validate --strict` does not catch this,
  so a test does.
- The README shows the literal hook message for each surface, and says which
  of the three layers, voice, skills or hooks, does the work.

## v0.2.0

- Files written from the shell with `cat > file <<EOF`, `tee`, `echo` or
  `printf`, through `>`, `>>` or a pipe, get the same comment and prose lints
  as an edit. `sed -i` is not followed.
- Every pattern inside a rule has a stable sub-id (`H2a`..`H2d`, `H4a`,
  `H4b`, `S5a`..`S5f`, `S6a`..`S6c`, `S7a`, `S7b`). Reasons print it and
  `disable:` takes either the family or one sub-id.
- Codex: portable root `plugin.json` with the OpenAI extension, a native
  `.agents/plugins/marketplace.json`, and `agents/openai.yaml` files that keep
  `setup` and `sync` out of implicit invocation. Skill directories now match
  their frontmatter names; `/unwordy:setup` and friends are unchanged.
- Cursor: a `sessionStart` hook injects the voice, `beforeShellExecution`
  lints every shell command, and Cursor's `preToolUse` `Shell` payload is
  understood as well.
- Repositories with commitlint or a commit template keep their own subject
  rules: S5a and S6c skip commit messages there.
- Per-surface limits: `pr.max_body_lines`, `commit.max_subject`,
  `comment.max_bullets` and the like override the flat key for one surface.
- `templates/` with `team-strict`, `team-qa` and `team-enterprise`;
  `/unwordy:setup --project <template>` starts from one.
- German banned words next to the Polish list.
- `evals/` with one `claude plugin eval` case per surface, regex graders only.
- Always-on cost ~281 tokens; the session-start voice stays about 260.

## v0.1.0

First release.

- Style profile in Markdown with flat frontmatter, resolved from
  `$UNWORDY_STYLE`, `.unwordy.md` up to the git root, or
  `~/.config/unwordy/style.md`, falling back to the `senior` preset. Presets:
  lazy, senior, qa, lead, formal, custom.
- Session start injects the core rules plus the chosen voice, about 260 tokens.
- Skills `/unwordy:setup`, `/unwordy:sync`, `/unwordy:rewrite` and the
  model-loaded `unwordy-write`. Always-on listing cost ~297 tokens.
- Hooks with no model-token cost: comment lints on `Edit`, `Write`,
  `MultiEdit`, `NotebookEdit` and Codex `apply_patch`; commit, PR, issue and
  tracker lints on `git`, `gh` and `glab` commands; text-field lints on MCP
  calls; an optional reply check on `Stop` under `strict: block`.
- Rules H1-H4 deny, S1-S7 warn or deny by `strict`. Every reason names its
  rule id. After two denials of the same rule on the same target in a session,
  that rule drops to a warning.
- Exemptions for license headers, shebangs, encoding lines, linter directives,
  generated files, fixtures, snapshots, lock files and the profile's `ignore`
  globs. `UNWORDY_OFF=1` and `enabled: false` turn everything off.
- Adapters: Codex plugin manifest and hook template, Cursor plugin manifest and
  `beforeShellExecution` template, `AGENTS.md` and `.cursor/rules/unwordy.mdc`
  rendering through `/unwordy:sync`.
