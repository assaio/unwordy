"""Package the committed plugin and standalone skill without local state."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    destination = Path(sys.argv[1])
    if git("status", "--porcelain").strip():
        raise ValueError("commit the release before packaging")
    version = json.loads(git("show", "HEAD:plugin.json"))["version"]
    destination.mkdir(parents=True, exist_ok=True)
    files = [path.decode() for path in git("ls-files", "-z").split(b"\0") if path]
    artifacts = []
    for name, selected, prefix in (
        (f"unwordy-{version}.zip", files, ""),
        (f"unwordy-skill-{version}.zip", [path for path in files if path.startswith("skills/unwordy/")], "skills/"),
    ):
        path = destination / name
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in selected:
                info = zipfile.ZipInfo(source.removeprefix(prefix))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, git("show", f"HEAD:{source}"))
        artifacts.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (destination / "SHA256SUMS").write_text("\n".join(artifacts) + "\n")
    print("\n".join(artifacts))


if __name__ == "__main__":
    main()
