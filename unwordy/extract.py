"""Pull lintable text out of tool calls: added lines, comments, shell messages, MCP fields."""

import difflib
import json
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

MAX_BYTES = 1_000_000
MAX_LINES = 20_000


@dataclass(frozen=True)
class Syntax:
    line: tuple = ()
    block: tuple = ()
    quotes: str = "\"'"
    multiline: tuple = ()
    docstring: bool = False


TEXT = Syntax()
HASH = Syntax(line=("#",))
PYTHON = Syntax(line=("#",), multiline=('"""', "'''"), docstring=True)
C_LIKE = Syntax(line=("//",), block=(("/*", "*/"),))
JS_LIKE = Syntax(line=("//",), block=(("/*", "*/"),), multiline=("`",))
RUST = Syntax(line=("//",), block=(("/*", "*/"),), quotes='"')
CSS = Syntax(block=(("/*", "*/"),))
SCSS = Syntax(line=("//",), block=(("/*", "*/"),))
SQL = Syntax(line=("--",), block=(("/*", "*/"),))
LUA = Syntax(line=("--",), block=(("--[[", "]]"),))
HASKELL = Syntax(line=("--",), block=(("{-", "-}"),))
LISP = Syntax(line=(";",), quotes='"')
MARKUP = Syntax(block=(("<!--", "-->"),), quotes="")
PHP = Syntax(line=("//", "#"), block=(("/*", "*/"),))
HCL = Syntax(line=("#", "//"), block=(("/*", "*/"),))
INI = Syntax(line=("#", ";"))
PERCENT = Syntax(line=("%",))

_BY_SUFFIX = {
    **dict.fromkeys((".py", ".pyi"), PYTHON),
    **dict.fromkeys((".sh", ".bash", ".zsh", ".fish", ".rb", ".pl", ".pm", ".r",
                     ".yaml", ".yml", ".toml", ".cfg", ".conf", ".ex", ".exs",
                     ".nix", ".cmake", ".mk", ".ps1", ".jl", ".cr", ".nim",
                     ".coffee", ".gd", ".tcl", ".properties", ".dockerfile"), HASH),
    **dict.fromkeys((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".m", ".mm",
                     ".cs", ".java", ".kt", ".kts", ".scala", ".groovy", ".gradle",
                     ".swift", ".dart", ".proto", ".sol", ".zig", ".jsonc", ".json5",
                     ".glsl", ".hlsl"), C_LIKE),
    **dict.fromkeys((".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
                     ".go"), JS_LIKE),
    ".rs": RUST,
    ".css": CSS,
    **dict.fromkeys((".scss", ".less"), SCSS),
    ".sql": SQL,
    ".lua": LUA,
    **dict.fromkeys((".hs", ".elm"), HASKELL),
    **dict.fromkeys((".lisp", ".el", ".clj", ".cljs", ".scm", ".rkt"), LISP),
    **dict.fromkeys((".html", ".htm", ".xml", ".svg"), MARKUP),
    ".php": PHP,
    **dict.fromkeys((".tf", ".hcl"), HCL),
    ".ini": INI,
    **dict.fromkeys((".tex", ".erl", ".hrl"), PERCENT),
    **dict.fromkeys((".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc", ".org"), TEXT),
}

_BY_NAME = {
    **dict.fromkeys(("dockerfile", "containerfile", "makefile", "gnumakefile",
                     "rakefile", "gemfile", "vagrantfile", "cmakelists.txt",
                     ".gitignore", ".dockerignore", ".env", ".bashrc", ".zshrc",
                     ".editorconfig"), HASH),
}


def syntax_for(path):
    """Comment syntax for a path, TEXT for prose files, None when unknown."""
    name = os.path.basename(str(path)).lower()
    if name in _BY_NAME:
        return _BY_NAME[name]
    return _BY_SUFFIX.get(os.path.splitext(name)[1])


@dataclass
class Line:
    text: str
    kind: str = "blank"
    comment: str = ""
    doc: bool = False
    cont: bool = False


class _ScanState:
    def __init__(self):
        self.block = None
        self.block_doc = False
        self.docstring = None
        self.string = None
        self.expect_doc = True


_DOCSTART = re.compile(r"[rRuUbBfF]{0,2}(\"\"\"|''')")
_BLOCK_OPEN = re.compile(r":\s*(?:#.*)?$")
_COMMENT_EDGE = re.compile(r"^[\s*/!#;%-]+")


def scan(lines, syntax):
    """Classify each line as blank, code, comment or mixed and pull out comment text."""
    state = _ScanState()
    return [_scan_line(text, syntax, state) for text in lines]


def _scan_line(text, syntax, state):
    parts = []
    code = False
    cont = state.string is not None
    doc = bool(state.docstring) or (state.block is not None and state.block_doc)
    touched = state.block is not None or state.docstring is not None
    i, n = 0, len(text)
    while i < n:
        if state.string:
            j = text.find(state.string, i)
            code = True
            if j == -1:
                break
            i, state.string = j + len(state.string), None
            continue
        if state.docstring:
            j = text.find(state.docstring, i)
            if j == -1:
                parts.append(text[i:])
                break
            parts.append(text[i:j])
            i, state.docstring = j + 3, None
            continue
        if state.block:
            j = text.find(state.block, i)
            if j == -1:
                parts.append(text[i:])
                break
            parts.append(text[i:j])
            i, state.block = j + len(state.block), None
            continue
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if syntax.docstring and not code and state.expect_doc:
            m = _DOCSTART.match(text, i)
            if m:
                quote = m.group(1)
                j = text.find(quote, m.end())
                touched = doc = True
                if j == -1:
                    parts.append(text[m.end():])
                    state.docstring = quote
                    break
                parts.append(text[m.end():j])
                i = j + 3
                continue
        hit = False
        for start, end in syntax.block:
            if text.startswith(start, i):
                touched = hit = True
                is_doc = start == "/*" and text.startswith("/**", i) and not text.startswith("/**/", i)
                doc = doc or is_doc
                j = text.find(end, i + len(start))
                if j == -1:
                    parts.append(text[i + len(start):])
                    state.block, state.block_doc = end, is_doc
                    i = n
                else:
                    parts.append(text[i + len(start):j])
                    i = j + len(end)
                break
        if hit:
            continue
        escaped = i > 0 and text[i - 1] == "\\"
        for marker in syntax.line:
            if escaped:
                break
            if text.startswith(marker, i) and (marker != "#" or i == 0 or text[i - 1].isspace()):
                touched = hit = True
                rest = text[i + len(marker):]
                doc = doc or (marker == "//" and rest[:1] in ("/", "!"))
                parts.append(rest)
                i = n
                break
        if hit:
            break
        for quote in syntax.multiline:
            if text.startswith(quote, i):
                hit = code = True
                j = text.find(quote, i + len(quote))
                if j == -1:
                    state.string = quote
                    i = n
                else:
                    i = j + len(quote)
                break
        if hit:
            continue
        code = True
        if ch in syntax.quotes and not (ch == "'" and i > 0 and text[i - 1].isalnum()):
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        i += 1
    comment = " ".join(_COMMENT_EDGE.sub("", p).strip() for p in parts).strip()
    if touched and not code:
        kind = "comment"
    elif touched:
        kind = "mixed"
    elif code:
        kind = "code"
    else:
        kind = "blank"
    if state.string is not None:
        state.expect_doc = False
    elif state.docstring is None:
        if kind in ("code", "mixed"):
            state.expect_doc = _BLOCK_OPEN.search(text) is not None
        elif doc:
            state.expect_doc = False
    return Line(text, kind, comment, doc and touched, cont)


@dataclass
class Change:
    path: str
    lines: List[str]
    added: Set[int] = field(default_factory=set)
    partial: bool = False


def edit_changes(tool_name, tool_input, cwd, want=None):
    """Files an edit tool is about to change, with the indices of added lines.

    `want(path)` lets the caller rule a file out before it is read or diffed.
    """
    if not isinstance(tool_input, dict):
        return []
    if tool_name == "apply_patch":
        changes = _apply_patch(str(tool_input.get("command") or tool_input.get("input") or ""), cwd)
        return [c for c in changes if want is None or want(c.path)]
    if tool_name == "NotebookEdit":
        change = _notebook(tool_input, cwd)
        return [change] if change and (want is None or want(change.path)) else []
    path = _abspath(tool_input.get("file_path"), cwd)
    if not path or (want is not None and not want(path)):
        return []
    current = _read(path)
    if current is None:
        return []
    if tool_name == "Write":
        after = str(tool_input.get("content") or "")
    elif tool_name == "MultiEdit":
        after = current
        for edit in tool_input.get("edits") or []:
            if isinstance(edit, dict):
                after = _replace(after, edit)
    else:
        old = str(tool_input.get("old_string") or "")
        if old and old not in current:
            return _one(_diff(path, old, str(tool_input.get("new_string") or ""), partial=True))
        after = _replace(current, tool_input)
    return _one(_diff(path, current, after))


def _one(change):
    return [change] if change else []


def _replace(text, edit):
    old = str(edit.get("old_string") or "")
    new = str(edit.get("new_string") or "")
    if not old:
        return new + text
    if old not in text:
        return text
    return text.replace(old, new, -1 if edit.get("replace_all") else 1)


def _diff(path, before, after, partial=False):
    a, b = before.splitlines(), after.splitlines()
    if len(a) > MAX_LINES or len(b) > MAX_LINES:
        return None
    if not a:
        return Change(path, b, set(range(len(b))), partial)
    matcher = difflib.SequenceMatcher(None, a, b)
    added = set()
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            added.update(range(j1, j2))
    return Change(path, b, added, partial)


def _abspath(path, cwd):
    if not path:
        return ""
    path = os.path.expanduser(str(path))
    return path if os.path.isabs(path) else os.path.join(cwd or os.getcwd(), path)


def _read(path):
    """File text, "" when the file does not exist, None when it cannot be linted."""
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""
    except OSError:
        return None


_NOTEBOOK_SUFFIX = {"python": ".py", "r": ".r", "julia": ".jl", "javascript": ".js",
                    "typescript": ".ts", "scala": ".scala", "ruby": ".rb"}


def _notebook(tool_input, cwd):
    path = _abspath(tool_input.get("notebook_path"), cwd)
    mode = tool_input.get("edit_mode") or "replace"
    if not path or mode == "delete":
        return None
    old, cell_type, language = "", tool_input.get("cell_type"), "python"
    try:
        with open(path, encoding="utf-8") as handle:
            notebook = json.load(handle)
        language = str(notebook.get("metadata", {}).get("language_info", {}).get("name") or "python")
        if mode == "replace":
            for cell in notebook.get("cells", []):
                if cell.get("id") == tool_input.get("cell_id"):
                    source = cell.get("source", "")
                    old = "".join(source) if isinstance(source, list) else str(source)
                    cell_type = cell_type or cell.get("cell_type")
                    break
    except (OSError, ValueError, AttributeError):
        pass
    suffix = ".md" if cell_type == "markdown" else _NOTEBOOK_SUFFIX.get(language.lower(), ".py")
    return _diff(path + suffix, old, str(tool_input.get("new_source") or ""))


def _apply_patch(patch, cwd):
    changes, current = [], None
    for line in patch.splitlines():
        if line.startswith("*** "):
            header = line[4:]
            for prefix, partial in (("Add File: ", False), ("Update File: ", True)):
                if header.startswith(prefix):
                    current = Change(_abspath(header[len(prefix):].strip(), cwd), [], set(), partial)
                    changes.append(current)
                    break
            else:
                if header.startswith("Move to: ") and current is not None:
                    current.path = _abspath(header[len("Move to: "):].strip(), cwd)
                elif not header.startswith("End of File"):
                    current = None
            continue
        if current is None or line.startswith("@@"):
            continue
        if line.startswith("+"):
            current.added.add(len(current.lines))
            current.lines.append(line[1:])
        elif line.startswith(" ") or line == "":
            current.lines.append(line[1:])
    return changes


@dataclass
class Message:
    surface: str
    target: str
    title: str = ""
    body: str = ""
    meta: str = ""


_HEREDOC_SUB = re.compile(
    r"\$\(\s*cat\s*<<(-?)\s*(['\"]?)([\w-]+)\2[^\n]*\n(.*?)\n[ \t]*\3[ \t]*\n?\s*\)", re.S
)
_HEREDOC = re.compile(r"<<(-?)[ \t]*(['\"]?)([\w-]+)\2([^\n]*)\n(.*?)\n[ \t]*\3[ \t]*(?=\n|$)", re.S)
_PLACEHOLDER = "UNWORDYHEREDOC{}X"
_FD_REDIRECT = re.compile(r"(?<=\s)\d(?=>)")
_FD = "UNWORDYFDX"
_SEPARATORS = set(";&|\n")
_PUNCTUATION = _SEPARATORS | set("()")
_REDIRECTS = {"<", ">", ">>", "<<", "<<-", ">&", "<&", "&>", ">|", "<<<"}
_WRAPPERS = {"sudo", "command", "builtin", "exec", "time", "nohup", "env", "then",
             "do", "else", "elif", "if", "while", "until", "!", "(", "{", "(("}
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


@dataclass
class _Segment:
    args: List[str] = field(default_factory=list)
    stdin: Optional[str] = None
    targets: List[tuple] = field(default_factory=list)
    piped: bool = False


def _parse(command):
    """Simple commands of a command line: arguments, heredoc stdin, stdout redirect targets."""
    heredocs = []

    def stash(body, dash):
        if dash:
            body = "\n".join(part.lstrip("\t") for part in body.split("\n"))
        heredocs.append(body)
        return _PLACEHOLDER.format(len(heredocs) - 1)

    command = _HEREDOC_SUB.sub(lambda m: stash(m.group(4), m.group(1)), command)
    command = _HEREDOC.sub(lambda m: "<< " + stash(m.group(5), m.group(1)) + m.group(4), command)
    command = _FD_REDIRECT.sub(_FD, command.replace("\\\n", " "))
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>()\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []

    def restore(token):
        for index, body in enumerate(heredocs):
            token = token.replace(_PLACEHOLDER.format(index), body)
        return token

    segments = []
    for words, piped in _segments(tokens):
        segment = _Segment(piped=piped)
        skip = fd = False
        for index, token in enumerate(words):
            if skip:
                skip = False
                continue
            if token == _FD:
                fd = True
                continue
            if token in _REDIRECTS:
                skip = index + 1 < len(words)
                target = restore(words[index + 1]) if skip else ""
                if fd:
                    fd = False
                elif token in ("<<", "<<-"):
                    segment.stdin = target
                elif token == "<<<":
                    segment.stdin = target + "\n"
                elif token in (">", ">>", ">|") and target:
                    segment.targets.append((token == ">>", target))
                continue
            segment.args.append(restore(token))
        segments.append(segment)
    return segments


def _segments(tokens):
    segment, piped = [], False
    for token in tokens:
        if token and set(token) <= _PUNCTUATION:
            if set(token) & _SEPARATORS:
                if segment:
                    yield segment, piped
                segment, piped = [], token in ("|", "|&")
            continue
        segment.append(token)
    if segment:
        yield segment, piped


def shell_messages(command, cwd):
    """Messages a shell command would publish through git, gh or glab."""
    messages = []
    for segment in _parse(command):
        message = _message(_command(segment.args), cwd, segment.stdin)
        if message:
            messages.append(message)
    return messages


def shell_writes(command, cwd, want=None):
    """Files a shell command writes through a redirect or tee, when their text is in the command.

    cat, echo and printf are the producers, also through a pipe. In-place editors such as
    sed -i are not followed.
    """
    changes, piped = [], None
    for segment in _parse(command):
        args = _command(segment.args)
        stdin = segment.stdin if segment.stdin is not None else piped if segment.piped else None
        piped = content = _output(args, stdin)
        if content is None:
            continue
        for append, target in _sinks(args, segment.targets):
            path = _abspath(target, cwd)
            if path.startswith("/dev/") or (want is not None and not want(path)):
                continue
            current = _read(path)
            if current is None:
                continue
            after = content
            if append and current:
                after = current + ("" if current.endswith("\n") else "\n") + content
            change = _diff(path, current, after)
            if change and change.added:
                changes.append(change)
    return changes


_ECHO_FLAGS = re.compile(r"-[neE]+")
_CONVERSION = re.compile(r"%[-+ #0-9.]*([a-zA-Z%])")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\"}


def _output(args, stdin):
    """What cat, tee, echo or printf print, or None when the text is not in the command."""
    if not args:
        return None
    name = os.path.basename(args[0])
    if name == "tee":
        return stdin
    if name == "cat":
        return stdin if all(a.startswith("-") for a in args[1:]) else None
    if name == "echo":
        rest = list(args[1:])
        flags = ""
        while rest and _ECHO_FLAGS.fullmatch(rest[0]):
            flags += rest.pop(0)
        text = " ".join(rest)
        text = _unescape(text) if "e" in flags else text
        return text if "n" in flags else text + "\n"
    if name == "printf":
        return _printf(args[2:] if args[1:2] == ["--"] else args[1:])
    return None


def _sinks(args, targets):
    sinks = list(targets)
    if args and os.path.basename(args[0]) == "tee":
        options = [a for a in args[1:] if a.startswith("-") and a != "-"]
        append = any(o == "--append" or (not o.startswith("--") and "a" in o) for o in options)
        sinks += [(append, a) for a in args[1:] if a not in options and a != "-"]
    return sinks


def _unescape(text):
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(0)), text)


def _printf(args):
    if not args:
        return None
    fmt, values, out = _unescape(args[0]), list(args[1:]), []
    consumes = any(m.group(1) != "%" for m in _CONVERSION.finditer(fmt))

    def fill(match):
        letter = match.group(1)
        if letter == "%":
            return "%"
        value = values.pop(0) if values else ""
        return _unescape(value) if letter == "b" else value

    while True:
        out.append(_CONVERSION.sub(fill, fmt))
        if not values or not consumes:
            break
    return "".join(out)


def _command(args):
    i = 0
    while i < len(args) and (args[i] in _WRAPPERS or _ASSIGNMENT.match(args[i])):
        i += 1
    return args[i:]


def _options(args, long_opts, short_opts):
    found = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            break
        if arg.startswith("--"):
            name, eq, value = arg.partition("=")
            if name in long_opts:
                if not eq:
                    if i + 1 >= len(args):
                        break
                    i += 1
                    value = args[i]
                if long_opts[name]:
                    found.setdefault(long_opts[name], []).append(value)
        elif arg.startswith("-") and len(arg) > 1:
            for k, letter in enumerate(arg[1:], 1):
                if letter in short_opts:
                    value = arg[k + 1:]
                    if not value:
                        if i + 1 >= len(args):
                            break
                        i += 1
                        value = args[i]
                    if short_opts[letter]:
                        found.setdefault(short_opts[letter], []).append(value)
                    break
        i += 1
    return found


_GIT_GLOBAL_VALUES = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
_COMMIT_LONG = {"--message": "message", "--file": "file", "--trailer": "meta", "--author": "meta",
                "--reuse-message": None, "--reedit-message": None, "--template": None,
                "--date": None, "--cleanup": None, "--fixup": None, "--squash": None,
                "--pathspec-from-file": None}
_COMMIT_SHORT = {"m": "message", "F": "file", "C": None, "c": None, "t": None}

_GH_TARGETS = {("pr", "create"): "pr", ("pr", "edit"): "pr", ("pr", "comment"): "comment",
               ("pr", "review"): "comment", ("issue", "create"): "issue",
               ("issue", "edit"): "issue", ("issue", "comment"): "comment"}
_GH_LONG = {"--title": "title", "--body": "body", "--body-file": "file", "--repo": None}
_GH_SHORT_TITLED = {"t": "title", "b": "body", "F": "file", "R": None}
_GH_SHORT = {"b": "body", "F": "file", "R": None}

_GLAB_TARGETS = {("mr", "create"): "pr", ("mr", "update"): "pr", ("mr", "note"): "comment",
                 ("mr", "comment"): "comment", ("issue", "create"): "issue",
                 ("issue", "update"): "issue", ("issue", "note"): "comment",
                 ("issue", "comment"): "comment"}
_GLAB_LONG = {"--title": "title", "--description": "body", "--message": "body", "--repo": None}
_GLAB_SHORT = {"t": "title", "d": "body", "m": "body", "R": None}

_GH_API_LONG = {"--field": "field", "--raw-field": "field", "--method": None, "--input": None}
_GH_API_SHORT = {"f": "field", "F": "field", "X": None}

TEXT_KEYS = {"body", "comment", "description", "summary", "text", "content", "message", "note"}


def _message(args, cwd, stdin):
    if not args:
        return None
    name = os.path.basename(args[0])
    if name == "git":
        return _git(args[1:], cwd, stdin)
    if name == "gh" and len(args) > 2:
        if args[1] == "api":
            return _gh_api(args[2:])
        surface = _GH_TARGETS.get((args[1], args[2]))
        if surface:
            short = _GH_SHORT_TITLED if surface in ("pr", "issue") else _GH_SHORT
            return _tracker(surface, f"gh {args[1]} {args[2]}", _options(args[3:], _GH_LONG, short), cwd, stdin)
    if name == "glab" and len(args) > 2:
        surface = _GLAB_TARGETS.get((args[1], args[2]))
        if surface:
            return _tracker(surface, f"glab {args[1]} {args[2]}", _options(args[3:], _GLAB_LONG, _GLAB_SHORT), cwd, stdin)
    return None


def _git(args, cwd, stdin):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in _GIT_GLOBAL_VALUES else 1
    if i >= len(args) or args[i] != "commit":
        return None
    opts = _options(args[i + 1:], _COMMIT_LONG, _COMMIT_SHORT)
    if "file" in opts:
        text = _read_arg(opts["file"][-1], cwd, stdin)
    elif "message" in opts:
        text = "\n\n".join(part.strip("\n") for part in opts["message"])
    else:
        text = ""
    meta = "\n".join(opts.get("meta", []))
    if not text.strip() and not meta:
        return None
    subject, _, body = text.strip("\n").partition("\n")
    return Message("commit", "git commit", subject, body.strip("\n"), meta)


def _tracker(surface, target, opts, cwd, stdin):
    title = opts.get("title", [""])[-1]
    body = opts.get("body", [""])[-1]
    if "file" in opts:
        body = _read_arg(opts["file"][-1], cwd, stdin)
    if not (title.strip() or body.strip()):
        return None
    return Message(surface, target, title, body)


def _gh_api(args):
    for field_value in _options(args, _GH_API_LONG, _GH_API_SHORT).get("field", []):
        key, _, value = field_value.partition("=")
        if key.lower() in TEXT_KEYS and value.strip() and not value.startswith("@"):
            return Message("comment", "gh api", "", value)
    return None


def _read_arg(value, cwd, stdin):
    if value == "-":
        return stdin or ""
    path = _abspath(value, cwd)
    text = _read(path) if path else None
    return text or ""


def mcp_fields(tool_input, min_length=40):
    """(key, text) pairs for long string fields named like body, comment, description."""
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except ValueError:
            return []
    found = []

    def walk(value, key):
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, str(child_key))
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str) and len(value.strip()) > min_length and key_words(key) & TEXT_KEYS:
            found.append((key, value))

    walk(tool_input, "")
    return found


def key_words(key):
    return {word.lower() for word in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", key)}


def read_transcript_tail(path, max_bytes=262_144):
    """Last user prompt and last assistant text from a Claude Code transcript, best effort."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            handle.seek(max(0, size - max_bytes))
            lines = handle.read().decode("utf-8", "replace").splitlines()
    except (OSError, TypeError, ValueError):
        return "", ""
    question, reply = "", ""
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("isMeta"):
            continue
        message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
        text = _text_of(message.get("content"))
        if entry.get("type") == "assistant" and not reply and text:
            reply = text
        elif entry.get("type") == "user" and text and not text.lstrip().startswith("<"):
            question = text
            break
    return question, reply


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [item.get("text") for item in content
                 if isinstance(item, dict) and item.get("type") == "text"]
        return "\n".join(part for part in parts if isinstance(part, str) and part)
    return ""


def relative_to(path, root):
    """Path relative to root with forward slashes, or the absolute path when outside."""
    try:
        rel = Path(path).resolve().relative_to(Path(root).resolve())
        return rel.as_posix()
    except (ValueError, OSError, RuntimeError):
        return Path(path).as_posix().lstrip("/")
