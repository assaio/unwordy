"""Package committed plugin, standalone skill and OpenAI directory candidate."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def directory_manifest():
    data = json.loads(git("show", "HEAD:.codex-plugin/plugin.json"))
    data.pop("hooks", None)
    data["keywords"] = [word for word in data["keywords"] if word != "hooks"]
    data["description"] = (
        "Personal and team writing guidance for commits, PRs, reviews, QA reports "
        "and design handoffs. Preserve supplied facts and repository conventions."
    )
    data["interface"]["longDescription"] = (
        "A portable skill for writing and rewriting in a personal or team voice. "
        "Choose role and tone independently, preserve supplied facts, uncertainty, "
        "test evidence and required templates. Missing details stay missing. "
        "This directory bundle provides model guidance; it includes no local checker "
        "or lifecycle hooks. Results depend on the host model."
    )
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()


def main():
    destination = Path(sys.argv[1])
    if git("status", "--porcelain").strip():
        raise ValueError("commit the release before packaging")
    version = json.loads(git("show", "HEAD:plugin.json"))["version"]
    destination.mkdir(parents=True, exist_ok=True)
    files = [path.decode() for path in git("ls-files", "-z").split(b"\0") if path]
    modes = {}
    for record in git("ls-tree", "-rz", "HEAD").split(b"\0"):
        if record:
            metadata, name = record.split(b"\t", 1)
            modes[name.decode()] = int(metadata.split()[0], 8)
    artifacts = []
    skill_files = [path for path in files if path.startswith("skills/unwordy/")]
    directory_files = skill_files + [".codex-plugin/plugin.json", "docs/assets/unwordy.svg", "LICENSE"]
    for name, selected, prefix, overrides in (
        (f"unwordy-{version}.zip", files, "", {}),
        (f"unwordy-skill-{version}.zip", skill_files, "skills/", {}),
        (f"unwordy-openai-{version}.zip", directory_files, "", {".codex-plugin/plugin.json": directory_manifest()}),
    ):
        path = destination / name
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in selected:
                info = zipfile.ZipInfo(source.removeprefix(prefix))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = modes[source] << 16
                content = overrides[source] if source in overrides else git("show", f"HEAD:{source}")
                archive.writestr(info, content)
        artifacts.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (destination / "SHA256SUMS").write_text("\n".join(artifacts) + "\n")
    print("\n".join(artifacts))


if __name__ == "__main__":
    main()
