"""Lint rules. H1..H4 always deny; S1..S7 warn, deny or stay silent per the profile's strict.

A rule with several patterns gives each one a sub-id (H2a, S5f); the family id is the first two
characters and is what `disable:` and the loop guard also accept.
"""

import os
import re
from dataclasses import dataclass

from . import extract


@dataclass
class Finding:
    rule: str
    reason: str
    target: str = ""

    @property
    def hard(self):
        return self.rule.startswith("H")

    @property
    def family(self):
        return self.rule[:2]

    def disabled(self, settings):
        disabled = settings.get("disable") or ()
        return self.rule in disabled or self.family in disabled

    def __str__(self):
        return f"unwordy {self.rule}: {self.reason}"


BUILTIN_IGNORES = (
    "tests/fixtures/**", "**/*.snap", "*.lock", "*.lockb", "*-lock.json", "*-lock.yaml",
    "*.lockfile", "go.sum", "npm-shrinkwrap.json", "Package.resolved", "packages.lock.json",
)

_H1 = re.compile(
    r"co-authored-by:[^\n]*?\b(?:claude|codex|cursor|chatgpt|copilot|gemini)\b"
    r"|generated (?:with|by) \[?(?:claude|codex|cursor|ai)\b(?![.(_-])"
    r"|made-with: *cursor\b"
    r"|claude-session:"
    r"|\U0001F916"
    r"|noreply@anthropic\.com|cursoragent@cursor\.com|noreply@openai\.com",
    re.I,
)
_H2_REFERENCE = re.compile(
    r"\bper the (?:task|ticket|issue|request|instructions)\b"
    r"|\bas (?:requested|instructed)\b"
    r"|\bas the (?:task|ticket|issue|request|instructions) "
    r"(?:asks|asked|requires|required|requests|requested|specifies|specified|says|said|describes|described)\b",
    re.I,
)
_H2_STEP = re.compile(r"^(?:step|task|phase) \d", re.I)
_H2_HISTORY = re.compile(
    r"^(?:added|updated|changed|removed|fixed|refactored) (?:this|to|for|per|as requested)\b", re.I
)
_TICKET = re.compile(r"\b([A-Z]{2,10})-\d{2,}\b")
_NOT_TICKETS = frozenset((
    "UTF", "UCS", "ISO", "IEC", "IEEE", "RFC", "CVE", "CWE", "GHSA", "ECMA", "ES", "PEP",
    "FIPS", "PKCS", "NIST", "ANSI", "SHA", "MD", "AES", "DES", "RSA", "HMAC", "CRC",
    "BLAKE", "PBKDF", "HTTP", "TLS", "SSL", "IPV", "WPA", "MPEG", "BASE", "ROT", "GPL",
    "LGPL", "AGPL", "MPL", "BSD", "EPL", "CC", "IA", "ARM", "AVX", "SSE", "INT", "UINT",
    "CP", "KOI", "EUC", "GB", "COVID", "RS", "EPSG", "ADR", "SOC", "PCI", "DSS", "GPT",
    "HTML", "CSS", "USB", "RAID", "DDR", "PCIE", "MIL", "NEMA", "DIN", "EN", "BS", "ASTM",
    "JIS", "SAE", "POSIX", "XDG", "ASCII", "LATIN", "WIN", "IBM", "OAUTH", "SAML", "WCAG",
    "ITU", "ETSI", "DOI", "ERR", "NFPA", "UL", "IP", "TCP", "UDP", "AMD", "NVIDIA",
))
_H3 = re.compile(
    "^(?:Here['\u2019]s\\b|Here is\\b|Let me\\b|I['\u2019]ve\\b|I have\\b|Note that I\\b"
    "|As requested\\b|Hope this helps\\b|Sure[,!]|Certainly\\b)"
)
_H4_OPENER = re.compile(
    r"^(?:this|the) (?:function|method|class|file|module|component|hook) "
    r"(?:is|does|handles|provides|returns|takes|defines|represents|contains)\b",
    re.I,
)
_WHY = re.compile(
    r"\b(?:because|since|otherwise|unless|in case|due to|to avoid|to prevent|workaround"
    r"|must|cannot|can't|never|so that)\b|,\s*so\b",
    re.I,
)
_H4_ECHO = re.compile(
    r"^(?:import|return|increment|initialize|define|create|set|get|call|loop|check)"
    r"(?: (?:the|a|an))? ?(\w+) *$",
    re.I,
)
_DASH = re.compile("\u2014|\\s\u2013\\s")
_BULLET = re.compile(r"^\s*[-*+]\s+\S")
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_LABEL = re.compile(r"^\s*[-*+]\s+\*\*[^*\n]+?(?::\*\*|\*\*:)")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]")
_S6_SUMMARY = re.compile(r"^\s*#+\s*summary\s*$", re.I | re.M)
_S6_TEST_PLAN = re.compile(r"^\s*#+\s*test(?:ing)? plan\s*$", re.I | re.M)
_S6_CHANGES = re.compile(r"^\W*summary of changes\b", re.I | re.M)
_S6_OPENER = re.compile(
    r"^this (?:pr|pull request|commit|change) (?:adds|implements|introduces)\b", re.I
)
_CLOSING = re.compile(r"^\W*(?:let me know if|feel free to)\b", re.I)
_YES_NO = re.compile(
    r"^(?:is|are|was|were|do|does|did|can|could|should|would|will|has|have|had|may|might"
    r"|must|isn't|aren't|doesn't|don't|didn't|can't|won't|shouldn't)\b",
    re.I,
)
_ONE_FACT = re.compile(r"^(?:what|which|where|when|who|whose|how many|how much|how long|how old)\b", re.I)
_FENCE = re.compile(r"^\s*(?:```|~~~)")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LIST_MARKER = re.compile(r"^\s*(?:[-*+>]|\d+[.)])\s+")
_DIRECTIVE = re.compile(
    r"noqa|eslint-(?:disable|enable)|\btype:|@ts-|pragma|nolint|pylint:|prettier-ignore"
    r"|rubocop:|istanbul ignore|c8 ignore|biome-ignore|fmt:\s*(?:off|on|skip)|nosec",
    re.I,
)
_LICENSE = re.compile(
    r"copyright|spdx-license-identifier|licensed under|all rights reserved"
    r"|permission is hereby granted",
    re.I,
)
_ENCODING = re.compile(r"coding[:=]|-\*-|\bvim?:", re.I)
_GENERATED_PROSE = re.compile(
    r"@generated\b|\bDO NOT EDIT\b|\bgenerated automatically\b"
    r"|\b(?:auto-?|automatically |machine[- ])generated\b"
    r"|\bthis (?:file|document|page) (?:is|was) generated\b",
    re.I,
)
_GENERATED = re.compile(
    _GENERATED_PROSE.pattern + r"|\bcode generated\b|\bthis code (?:is|was) generated\b"
    r"|\bgenerated (?:by|from|with) [\w./-]+",
    re.I,
)
_PY_DEF = re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)")
_SIGNATURE_END = re.compile(r":\s*(?:#.*)?$")
_SIGNATURE_CLOSE = re.compile(r"\)\s*(?:->\s*[^:]+?)?\s*:")
_CALL_NAME = re.compile(r"(\w+)\s*(?:<[^>()]*>)?\s*\(")

_WHERE = {"commit": "the commit message", "pr": "the PR text", "issue": "the issue text",
          "comment": "the comment", "reply": "the reply"}
_STRUCTURED_KEYS = {"body", "comment", "description", "message", "note"}


def lint_message(message, settings, conventions=False):
    """Commit, PR, issue and comment text extracted from a shell command.

    With `conventions`, the repo has its own commit format (commitlint, a commit template), so
    the subject length and opener checks stay out of its way for commits.
    """
    where = _WHERE.get(message.surface, "the message")
    prose = "\n".join(_prose_lines("\n".join(p for p in (message.title, message.body) if p)))
    findings = _attribution(prose + "\n" + message.meta, where, message.surface == "commit")
    findings += _dashes(prose, where) + _banned(prose, where, settings)
    findings += _structure(message.title, message.body, message.surface, where, settings)
    if message.surface in ("commit", "pr"):
        findings += _boilerplate(message.title, message.body, where)
    if conventions and message.surface == "commit":
        findings = [f for f in findings if f.rule not in ("S5a", "S6c")]
    return findings


def lint_field(key, text, settings):
    """A long text field of an MCP tool call, such as a Jira or GitHub comment body."""
    prose = "\n".join(_prose_lines(text))
    findings = _attribution(prose, "the comment", False) + _dashes(prose, "the comment")
    findings += _banned(prose, "the comment", settings)
    if extract.key_words(key) & _STRUCTURED_KEYS:
        findings += _structure("", text, "comment", "the comment", settings)
    return findings


def lint_reply(reply, question, settings):
    """The agent's last reply, checked by the Stop hook under strict: block."""
    lines = [line for line in (reply or "").splitlines() if line.strip()]
    findings = []
    kind = _question_kind(question)
    if kind and len(lines) > 12:
        findings.append(Finding(
            "S7a", f"{len(lines)}-line reply to a {kind} question. Answer again in a few lines."
        ))
    for line in _prose_lines(reply or ""):
        if _CLOSING.match(line.strip()):
            findings.append(Finding("S7b", f"closing offer ({_snippet(line.strip())}). End when the answer ends."))
            break
    return findings


def lint_change(change, settings, root):
    """Added lines of a file edit: comment lints for code, communication lints for prose."""
    syntax = extract.syntax_for(change.path)
    if syntax is None or not change.added or exempt_path(change.path, settings, root):
        return []
    if _generated(change, syntax):
        return []
    if syntax is extract.TEXT:
        return _lint_prose_file(change, settings)
    return _lint_code(change, syntax, settings)


def exempt_path(path, settings, root):
    rel = extract.relative_to(path, root)
    patterns = BUILTIN_IGNORES + tuple(settings.get("ignore") or ())
    return any(glob_match(rel, pattern) for pattern in patterns)


def glob_match(rel, pattern):
    """Match a relative path against a glob. Patterns match at any depth unless they start with /."""
    pattern = pattern.strip()
    if pattern.startswith("./"):
        pattern = pattern[2:]
    if not pattern:
        return False
    anchored = pattern.startswith("/")
    if pattern.endswith("/"):
        pattern += "**"
    pattern = pattern.lstrip("/")
    if "/" not in pattern and not anchored:
        return re.fullmatch(_glob_regex(pattern), rel.rsplit("/", 1)[-1]) is not None
    prefix = "" if anchored else "(?:.*/)?"
    return re.fullmatch(prefix + _glob_regex(pattern), rel) is not None


def _glob_regex(pattern):
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return "".join(out)


def _generated(change, syntax):
    head = change.lines[:5]
    if change.partial:
        text = extract._read(change.path)
        head = (text or "").splitlines()[:5]
    if syntax is extract.TEXT:
        return any(_GENERATED_PROSE.search(line) and not _H1.search(line) for line in head)
    comments = [line.comment for line in extract.scan(head, syntax) if line.comment]
    return any(_GENERATED.search(line) and not _H1.search(line) for line in comments)


def _lint_prose_file(change, settings):
    where = os.path.basename(change.path)
    hits = {}
    for index, text in _prose_indexed(change.lines):
        if index not in change.added:
            continue
        for finding in _attribution(text, where, False) + _dashes(text, where) + _banned(text, where, settings):
            hits.setdefault(finding.rule, []).append(finding)
        stripped = _LIST_MARKER.sub("", text).strip()
        if _H3.match(stripped):
            hits.setdefault("H3", []).append(Finding(
                "H3", f"chat phrasing in {where} ({_snippet(stripped)}). Write it as documentation, not as a reply."
            ))
    return _collapse(hits)


def _lint_code(change, syntax, settings):
    lines = change.lines
    info = extract.scan(lines, syntax)
    exempt = _exempt_lines(lines, info, change.partial)
    name = os.path.basename(change.path)
    hits = {}

    def hit(rule, reason):
        hits.setdefault(rule, []).append(Finding(rule, reason))

    for i in sorted(change.added):
        if i >= len(info) or i in exempt:
            continue
        line = info[i]
        text = line.comment
        if line.kind not in ("comment", "mixed") or not text:
            continue
        for finding in _attribution(text, "a code comment", False):
            hits.setdefault("H1", []).append(finding)
        _task_references(text, settings, hit)
        if _H3.match(text):
            hit("H3", f"chat phrasing in a code comment ({_snippet(text)}). Delete it or say why the code is this way.")
        if _H4_OPENER.match(text) and not _WHY.search(text):
            hit("H4a", f"comment restates the code ({_snippet(text)}). Delete it or say why.")
        elif line.kind == "comment" and not line.doc:
            echo = _H4_ECHO.match(text)
            nxt = _next_code(info, i)
            if echo and nxt is not None and echo.group(1).lower() in lines[nxt].lower():
                hit("H4b", f"comment restates the next line ({_snippet(text)}). Delete it.")
        for finding in _dashes(text, "a code comment") + _banned(text, "a code comment", settings):
            hits.setdefault(finding.rule, []).append(finding)

    comment_lines = sum(1 for i in change.added if i < len(info) and info[i].kind == "comment" and i not in exempt)
    code_lines = sum(1 for i in change.added if i < len(info) and info[i].kind in ("code", "mixed"))
    if code_lines >= 8 and comment_lines / code_lines > 0.3:
        hit("S3", f"{comment_lines} comment lines for {code_lines} code lines in {name}. Keep only comments that say why.")
    if not change.partial:
        for fn, doc_lines, body_lines in _long_docstrings(lines, info, syntax, change.added):
            hit("S4", f"docstring of {fn}() is {doc_lines} lines for a {body_lines}-line body. Cut it to what the signature does not say.")
    return _collapse(hits)


_H2 = (
    ("H2a", _H2_REFERENCE, "code comment points at the task"),
    ("H2b", _H2_STEP, "step number in a code comment"),
    ("H2c", _H2_HISTORY, "code comment describes the edit, not the code"),
)


def _task_references(text, settings, hit):
    for rule, pattern, what in _H2:
        if pattern.search(text):
            hit(rule, f"{what} ({_snippet(text)}). Say why the code is this way, or delete it.")
            return
    if settings.get("allow_ticket_refs"):
        return
    for ticket in _TICKET.finditer(text):
        if ticket.group(1) not in _NOT_TICKETS:
            hit("H2d", f"ticket id {ticket.group(0)} in a code comment. Put it in the commit message instead.")
            return


def _next_code(info, index):
    for j in range(index + 1, len(info)):
        if info[j].kind != "blank":
            return j if info[j].kind in ("code", "mixed") else None
    return None


def _exempt_lines(lines, info, partial):
    exempt = set()
    for i, line in enumerate(info):
        if line.kind not in ("comment", "mixed"):
            continue
        if not partial and i == 0 and lines[0].startswith("#!"):
            exempt.add(i)
        elif not partial and i < 2 and _ENCODING.search(line.comment):
            exempt.add(i)
        elif _DIRECTIVE.search(line.comment) or _LICENSE.search(line.comment):
            exempt.add(i)
    if not partial:
        header, started = [], False
        for i, line in enumerate(info):
            if line.kind == "comment":
                header.append(i)
                started = True
            elif line.kind == "blank" and not started or i in exempt:
                continue
            else:
                break
        if any(_LICENSE.search(info[i].comment) for i in header):
            exempt.update(header)
    return exempt


def _long_docstrings(lines, info, syntax, added):
    if syntax.docstring:
        yield from _python_docstrings(lines, info, added)
    elif "//" in syntax.line:
        yield from _brace_docstrings(lines, info, added)


def _indent(text):
    return len(text) - len(text.lstrip())


def _python_docstrings(lines, info, added):
    n = len(lines)
    for i, text in enumerate(lines):
        match = _PY_DEF.match(text)
        if not match:
            continue
        indent = len(match.group(1).expandtabs())
        j = i
        while j < min(n, i + 20) and not _SIGNATURE_CLOSE.search(lines[j]):
            j += 1
        if j >= min(n, i + 20) or not _SIGNATURE_END.search(lines[j]):
            continue
        start = next((k for k in range(j + 1, n) if lines[k].strip()), None)
        if start is None or not info[start].doc:
            continue
        end = start
        while end < n and info[end].doc:
            end += 1
        body = 0
        for k in range(end, n):
            if info[k].cont:
                body += 1
                continue
            if not lines[k].strip():
                continue
            if _indent(lines[k].expandtabs()) <= indent:
                break
            if info[k].kind in ("code", "mixed"):
                body += 1
        doc = end - start
        if doc > 3 and doc > body and added & set(range(start, end)):
            yield match.group(2), doc, body


def _brace_docstrings(lines, info, added):
    n, i = len(lines), 0
    while i < n:
        if not info[i].doc:
            i += 1
            continue
        start = i
        while i < n and info[i].doc:
            i += 1
        doc, decl = i - start, next((k for k in range(i, n) if lines[k].strip()), None)
        if decl is None or info[decl].kind not in ("code", "mixed") or "(" not in lines[decl]:
            continue
        head = lines[decl].strip()
        if head.endswith(";") or head.startswith(("@", "#")):
            continue
        depth, opened, inner, seen = 0, None, 0, 0
        for k in range(decl, min(n, decl + 2000)):
            if info[k].kind not in ("code", "mixed"):
                continue
            opens, closes = lines[k].count("{"), lines[k].count("}")
            if opened is None:
                seen += 1
                if seen > 4:
                    break
                if opens:
                    opened = k
                elif lines[k].rstrip().endswith(";"):
                    break
            depth += opens - closes
            if opened is not None and depth <= 0:
                break
            if opened is not None and k > opened:
                inner += 1
        name = _CALL_NAME.search(lines[decl])
        if opened is not None and doc > 3 and doc > inner and added & set(range(start, start + doc)):
            yield (name.group(1) if name else "function"), doc, inner


def _attribution(text, where, commit):
    match = _H1.search(text)
    if not match:
        return []
    again = "Remove it and commit again." if commit else "Remove it and try again."
    return [Finding("H1", f"attribution in {where} ({_snippet(match.group(0))}). {again}")]


def _dashes(text, where):
    if _DASH.search(text):
        return [Finding("S1", f"em dash in {where}. Use a comma, a colon or a full stop.")]
    return []


def _banned(text, where, settings):
    pattern = _banned_regex(tuple(settings.get("banned_words") or ()))
    match = pattern.search(text.replace("\u2019", "'")) if pattern else None
    if match:
        return [Finding("S2", f"'{match.group(0)}' in {where}. Use a plain word.")]
    return []


_BANNED_CACHE = {}


def _banned_regex(words):
    if words not in _BANNED_CACHE:
        parts = []
        for word in words:
            tokens = str(word).replace("\u2019", "'").split()
            if tokens:
                parts.append(r"\s+".join(re.escape(token) for token in tokens))
        parts.sort(key=len, reverse=True)
        _BANNED_CACHE[words] = (
            re.compile(r"(?<![\w-])(?:" + "|".join(parts) + r")(?![\w-])", re.I) if parts else None
        )
    return _BANNED_CACHE[words]


def _limit(settings, surface, key, default):
    """A per-surface override such as pr.max_body_lines, else the flat key, else the default."""
    return settings.get(f"{surface}.{key}") or settings.get(_FLAT.get(key, key)) or default


_FLAT = {"max_body_lines": "max_pr_body_lines"}


def _structure(title, body, surface, where, settings):
    findings = []
    limit = _limit(settings, surface, "max_subject", 72)
    if title and len(title) > limit:
        findings.append(Finding("S5a", f"subject is {len(title)} characters, over {limit}. Shorten it."))
    lines = [line for line in _prose_lines(body) if line.strip()]
    limit = _limit(settings, surface, "max_body_lines", 12)
    if len(lines) > limit:
        findings.append(Finding("S5b", f"{where} is {len(lines)} lines, over {limit}. Cut it to what a reviewer needs."))
    bullets = sum(1 for line in lines if _BULLET.match(line))
    limit = _limit(settings, surface, "max_bullets", 6)
    if bullets > limit:
        findings.append(Finding("S5c", f"{bullets} bullets in {where}, over {limit}. Keep the ones that matter."))
    headers = [line for line in lines if _HEADER.match(line)]
    if len(headers) > 2:
        findings.append(Finding("S5d", f"{len(headers)} markdown headers in {where}. Use plain paragraphs."))
    labels = sum(1 for line in lines if _LABEL.match(line))
    if labels > 3:
        findings.append(Finding("S5e", f"{labels} bold-label bullets in {where}. Write sentences."))
    if any(_EMOJI.search(line) for line in headers):
        findings.append(Finding("S5f", f"emoji in a header of {where}. Drop it."))
    return findings


def _boilerplate(title, body, where):
    findings = []
    text = "\n".join(_prose_lines(body))
    if _S6_SUMMARY.search(text) and _S6_TEST_PLAN.search(text):
        findings.append(Finding("S6a", f"'## Summary' plus '## Test plan' template in {where}. Say what, why and how tested in plain lines."))
    if _S6_CHANGES.search(text):
        findings.append(Finding("S6b", f"'Summary of changes' block in {where}. The diff is the summary."))
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    for line in (title.strip(), first):
        match = _S6_OPENER.match(line)
        if match:
            findings.append(Finding("S6c", f"opener '{match.group(0)}'. Start with the change itself."))
            break
    return findings


def _question_kind(question):
    question = (question or "").strip()
    if not question.endswith("?") or "\n" in question or len(question.split()) > 25:
        return None
    if _YES_NO.match(question):
        return "yes/no"
    if _ONE_FACT.match(question) and len(question.split()) <= 15:
        return "one-fact"
    return None


def _prose_indexed(lines):
    fenced = False
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield index, _INLINE_CODE.sub("", line)


def _prose_lines(text):
    return [line for _, line in _prose_indexed((text or "").splitlines())]


def _snippet(text, limit=60):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _collapse(hits):
    findings = []
    for rule in sorted(hits):
        first, more = hits[rule][0], len(hits[rule]) - 1
        suffix = f" ({more} more like this)" if more else ""
        findings.append(Finding(rule, first.reason + suffix))
    return findings
