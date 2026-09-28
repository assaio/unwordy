import json

import pytest

from unwordy import extract, hook, lint, profile


def configure(project, frontmatter, body=""):
    (project / ".unwordy.md").write_text(f"---\n{frontmatter}\n---\n{body}\n")
    return profile.resolve(project)


def call(project, tool, fields):
    return hook.run("pre-mcp", {"cwd": str(project), "tool_name": tool, "tool_input": fields})


def test_voice_respects_disabled_preferences_and_surface_limits(project):
    prof = configure(project, "disable: H2, H4, S1\npr.max_body_lines: 20\nrole: design\ntone: warm", "Keep dashes and ticket references.")
    text = prof.voice()
    assert "Prefer commas" not in text
    assert "Flag ticket" not in text
    assert "Review comments that restate" not in text
    assert "body 20 nonblank prose lines" in text
    assert "accessibility" in text and "Be warm" in text
    assert "Keep dashes and ticket references." in text


def test_disabled_profile_has_no_voice(project):
    assert configure(project, "enabled: false").voice() == ""


def test_lazy_tone_keeps_casual_punctuation_without_losing_filler_checks(project):
    settings = configure(project, "tone: lazy").settings
    message = extract.Message("comment", "test", "", "Quick note — we can remove this lock. "
                              "The caller holds it already. Seamlessly done.")
    effects = {finding.rule: lint.action(finding, settings)
               for finding in lint.lint_message(message, settings)}
    assert effects["S1"] == "ignore"
    assert effects["S2"] == "warn"
    long_title = extract.Message(
        "pr", "test",
        "A title that is deliberately longer than the usual seventy-two character preference",
        "The caller holds the lock.",
    )
    effects = {finding.rule: lint.action(finding, settings)
               for finding in lint.lint_message(long_title, settings)}
    assert effects["S5a"] == "ignore"


@pytest.mark.parametrize("entry", ["preset: typo", "strict: typo", "attribution: typo",
                                  "max_subject: -1", "pr.max_body_lines: 0", "enabled: maybe",
                                  "role: manager", "tone: terse", "rule.X1: warn",
                                  "rule.H4: deny", "disable: S99", "unknown: true",
                                  "pr.max_subject: many", "banana.attribution: allow"])
def test_bad_configuration_is_diagnosed_and_hooks_do_not_block(project, entry):
    prof = configure(project, entry)
    assert prof.diagnostics
    out = call(project, "mcp__github__create_pull_request", {"body": "Generated with Claude"})
    context = out["hookSpecificOutput"]
    assert "permissionDecision" not in context
    assert "configuration" in context["additionalContext"]


def test_duplicate_and_unclosed_frontmatter_are_diagnosed():
    assert profile.validate("---\ntone: warm\ntone: direct\n---")[0].endswith("duplicate setting")
    assert profile.validate("---\ntone: warm")[0].endswith("missing closing ---")


@pytest.mark.parametrize("text", ["This function returns the billing currency mandated by the merchant contract.",
                                  "Step 1: derive the challenge according to RFC 7636."])
def test_contract_and_standard_comments_are_kept(project, text):
    change = extract.Change(str(project / "api.py"), ["# " + text, "x = 1"], {0, 1})
    assert lint.lint_change(change, dict(profile.DEFAULTS), project) == []


@pytest.mark.parametrize("rule", ["H2b", "H2d", "H4a", "H4b"])
def test_heuristics_warn_by_default_and_allow_explicit_effects(rule):
    settings = dict(profile.DEFAULTS)
    finding = lint.Finding(rule, "")
    assert lint.action(finding, settings) == "warn"
    settings[f"rule.{rule[:2].lower()}"] = "block"
    assert lint.action(finding, settings) == "block"
    settings[f"rule.{rule.lower()}"] = "off"
    assert lint.action(finding, settings) == "ignore"


@pytest.mark.parametrize("path", [".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE/bug.md",
                                 "docs/PULL_REQUEST_TEMPLATE.md", ".gitlab/merge_request_templates/Default.md"])
def test_pr_templates_are_respected_across_shell_and_mcp(project, path):
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("## Summary\n## Risk\n## Test plan\n")
    prof = configure(project, "strict: block")
    body = "## Summary\nRetry delivery.\n## Risk\nDuplicates.\n## Test plan\nForced 502."
    required = profile.pr_headings(project, prof.settings)
    msg = extract.Message("pr", "test", "Retry delivery", body)
    assert lint.lint_message(msg, prof.settings, required_headings=required) == []
    assert call(project, "mcp__github__create_pull_request", {"title": "Retry delivery", "body": body}) is None
    extra = extract.Message("pr", "test", "Retry", body + "\n## More\n## Extra")
    assert "S5d" in [f.rule for f in lint.lint_message(extra, prof.settings, required_headings=required)]


def test_explicit_template_policy_handles_external_requirements(project):
    settings = configure(project, "pr_template: respect").settings
    msg = extract.Message("pr", "test", "Fix", "## Summary\nx\n## Test plan\ny")
    assert lint.lint_message(msg, settings) == []
    settings["pr_template"] = "ignore"
    assert "S6a" in [f.rule for f in lint.lint_message(msg, settings)]


@pytest.mark.parametrize("fields", [{"title": "Generated with Claude"},
                                    {"body": "Generated with Claude"},
                                    {"title": "Fix", "body": "Generated with Claude"}])
def test_mcp_uses_pr_disclosure_policy_and_checks_titles(project, fields):
    configure(project, "pr.attribution: allow\ncomment.attribution: block")
    assert call(project, "mcp__github__create_pull_request", fields) is None
    assert call(project, "mcp__github__add_issue_comment", fields)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_short_mcp_text_is_checked_and_reads_are_not(project):
    assert "S2" in call(project, "mcp__jira__add_comment", {"body": "leverage"})["hookSpecificOutput"]["additionalContext"]
    assert call(project, "mcp__jira__search", {"body": "Generated with Claude"}) is None
    assert call(project, "mcp__unknown__execute", {"body": "Generated with Claude"}) is None


def test_json_mcp_arguments_and_gh_api_have_the_same_pr_surface():
    fields = {"title": "Generated with Claude", "body": "Retry delivery."}
    mcp = extract.mcp_messages("mcp__github__create_pull_request", json.dumps(fields))[0]
    shell = extract.shell_messages('gh api repos/o/r/pulls -f title="Generated with Claude" -f body="Retry delivery."', ".")[0]
    assert (mcp.surface, mcp.title, mcp.body) == (shell.surface, shell.title, shell.body)


def test_quoted_source_is_not_rewritten_by_style_findings():
    msg = extract.Message("comment", "test", "", "> We leverage a robust approach — Generated with Claude.\nThe observed error is `robust_failure`.")
    assert lint.lint_message(msg, dict(profile.DEFAULTS)) == []
