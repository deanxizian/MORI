#!/usr/bin/env python3
"""Restore explicitly selected, hash-pinned MORI datasets without overwriting files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

REPOSITORY = "deanxizian/MORI"
SNAPSHOT = "48fe22aa75554c9d7bb237e2d2dcacca7f83dde1"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def destination(root, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid archive path: " + name)
    target = root / relative
    if target.is_symlink():
        raise ValueError("Refusing symlink destination: " + name)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError("Archive path escapes destination: " + name)
    return target


def download_request(entry):
    if entry["storage"] == "GIT":
        url = f"https://raw.githubusercontent.com/{REPOSITORY}/{SNAPSHOT}/" + quote(entry["path"], safe="/")
        return Request(url, headers={"User-Agent": "MORI-archive-restore"})
    if entry["storage"] != "GIT_LFS":
        raise ValueError("Unsupported storage type")
    payload = {"operation": "download", "transfers": ["basic"], "objects": [{"oid": entry["sha256"], "size": entry["bytes"]}]}
    request = Request(f"https://github.com/{REPOSITORY}.git/info/lfs/objects/batch", data=json.dumps(payload).encode(), headers={"Content-Type": "application/vnd.git-lfs+json", "Accept": "application/vnd.git-lfs+json"})
    with urlopen(request, timeout=60) as response:
        obj = json.load(response)["objects"][0]
    if "error" in obj or obj["oid"] != entry["sha256"] or obj["size"] != entry["bytes"]:
        raise RuntimeError("Archive LFS object unavailable or mismatched")
    action = obj["actions"]["download"]
    if urlsplit(action["href"]).scheme != "https":
        raise ValueError("Non-HTTPS archive download")
    return Request(action["href"], headers=action.get("header", {}))


def restore(root, entry):
    target = destination(root, entry["path"])
    if target.exists():
        if target.is_file() and target.stat().st_size == entry["bytes"] and digest(target) == entry["sha256"]:
            return "already present"
        raise FileExistsError("Existing file differs; retained unchanged: " + entry["path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    destination(root, entry["path"])
    temp = None
    try:
        h = hashlib.sha256()
        total = 0
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".mori-download-", delete=False) as output:
            temp = Path(output.name)
            with urlopen(download_request(entry), timeout=120) as response:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    total += len(block)
                    if total > entry["bytes"]:
                        raise ValueError("Download exceeds recorded size")
                    output.write(block)
                    h.update(block)
        if total != entry["bytes"] or h.hexdigest() != entry["sha256"]:
            raise ValueError("Archive SHA256 or size mismatch: " + entry["path"])
        # Hard-link publication is exclusive: never replace a file created meanwhile.
        os.link(temp, target)
        return "restored"
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List groups without downloading")
    parser.add_argument("--group", action="append", default=[], help="Restore a named manifest group")
    parser.add_argument("--path", action="append", default=[], help="Restore an exact manifest path")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Destination root; existing different files are never overwritten")
    args = parser.parse_args()
    manifest = json.loads((DEFAULT_ROOT / "docs/archive_assets.json").read_text())
    if manifest["snapshot"] != SNAPSHOT or manifest["repository"] != REPOSITORY:
        parser.error("Manifest source differs from pinned archive")
    groups = manifest["groups"]
    if args.list or not (args.group or args.path):
        for name, entries in groups.items():
            print(f"{name}: {len(entries)} files, {sum(e['bytes'] for e in entries) / 1048576:.1f} MiB")
        return
    all_entries = {e["path"]: e for entries in groups.values() for e in entries}
    selected = {}
    for name in args.group:
        if name not in groups:
            parser.error("Unknown group: " + name)
        selected.update({e["path"]: e for e in groups[name]})
    for name in args.path:
        if name not in all_entries:
            parser.error("Path is not in the manifest: " + name)
        selected[name] = all_entries[name]
    # Validate every destination before starting network or filesystem writes.
    for name, entry in selected.items():
        target = destination(args.root, name)
        if target.exists() and (not target.is_file() or target.stat().st_size != entry["bytes"] or digest(target) != entry["sha256"]):
            parser.error("Existing file differs; no downloads started: " + name)
    for name, entry in selected.items():
        print(restore(args.root, entry), name, flush=True)


if __name__ == "__main__":
    main()
