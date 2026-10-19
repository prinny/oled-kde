#!/usr/bin/env python3
"""Install and restore OLED KDE using only the Python standard library.

Installer design (backups, install record, dry run, component
selection) follows oled-gnome's theme.py. Unlike that helper, this
one only copies files: selecting the theme afterwards is one command
(printed on install) and needs no settings backup.
"""

import argparse
import configparser
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
LOOKANDFEEL = "io.local.oled.desktop"
COMPONENTS = ("plasma", "konsole", "ghostty", "editors", "firefox")


def locations():
    home = Path.home()
    return {
        "config": Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config"),
        "data": Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share"),
        "state": Path(os.environ.get("XDG_STATE_HOME") or home / ".local/state") / "oled-kde",
    }


def exists(path):
    return path.exists() or path.is_symlink()


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def firefox_profile():
    """Default Firefox profile directory, from profiles.ini."""
    paths = locations()
    for base in (paths["config"] / "mozilla/firefox", Path.home() / ".mozilla/firefox"):
        ini = base / "profiles.ini"
        if not ini.is_file():
            continue
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(ini, encoding="utf-8")
        except (configparser.Error, UnicodeDecodeError):
            continue  # Treat an unreadable profiles.ini as no profile there.
        install_default, profiles = None, []
        for section in parser.sections():
            if section.startswith("Install") and parser.has_option(section, "Default"):
                install_default = parser.get(section, "Default")
            elif section.startswith("Profile") and parser.has_option(section, "Path"):
                profiles.append((parser.get(section, "Default", fallback="0") == "1",
                                 parser.get(section, "IsRelative", fallback="1") == "1",
                                 parser.get(section, "Path")))
        if install_default:
            return base / install_default
        for is_default, is_relative, raw in sorted(profiles, reverse=True):
            return base / raw if is_relative else Path(raw)
    raise RuntimeError("No Firefox profile found (profiles.ini). Start Firefox once, "
                       "or install without the firefox component.")


def plan(component):
    """(target, source) pairs for a component ("all" means every component)."""
    paths = locations()
    data, config = paths["data"], paths["config"]
    targets = []
    if component in ("plasma", "all"):
        targets += [
            (data / "color-schemes/OLED.colors", SOURCE / "color-schemes/OLED.colors"),
            (data / "plasma/desktoptheme/oled", SOURCE / "plasma/desktoptheme/oled"),
            (data / "plasma/look-and-feel" / LOOKANDFEEL,
             SOURCE / "plasma/look-and-feel" / LOOKANDFEEL),
            (data / "org.kde.syntax-highlighting/themes/OLED.theme",
             SOURCE / "kate/OLED.theme"),
        ]
    if component in ("konsole", "all"):
        targets += [
            (data / "konsole/OLED.colorscheme", SOURCE / "konsole/OLED.colorscheme"),
            (data / "konsole/OLED.profile", SOURCE / "konsole/OLED.profile"),
        ]
    if component in ("ghostty", "all"):
        targets.append((config / "ghostty/themes/oled", SOURCE / "ghostty/oled"))
    if component in ("editors", "all"):
        targets += [
            (config / "nvim/colors/oled.lua", SOURCE / "editors/oled.lua"),
            (config / "helix/themes/oled.toml", SOURCE / "editors/oled.toml"),
            (config / "btop/themes/oled.theme", SOURCE / "editors/oled.theme"),
        ]
    if component in ("firefox", "all"):
        try:
            profile = firefox_profile()
        except RuntimeError:
            if component == "firefox":
                raise
            profile = None  # "all" skips Firefox when no profile exists.
        if profile is not None:
            targets += [
                (profile / "chrome/userChrome.css", SOURCE / "firefox/userChrome.css"),
                (profile / "chrome/userContent.css", SOURCE / "firefox/userContent.css"),
            ]
    return targets


def restore_files(records, recovery=None):
    for index, record in enumerate(reversed(records)):
        target = Path(record["target"])
        if recovery is not None and exists(target):
            copy(target, recovery / str(index) / target.name)
        remove(target)
        if record["backup"]:
            copy(Path(record["backup"]), target)


APPLY_HINTS = {
    "plasma": f"plasma-apply-lookandfeel -a {LOOKANDFEEL}   (keeps your desktop layout)",
    "konsole": "in Konsole, select the OLED profile or set its color scheme to OLED",
    "ghostty": "in Ghostty's config, set: theme = oled",
    "editors": "Neovim: colorscheme oled · Helix: theme = \"oled\" · btop: options → color theme oled",
    "firefox": "restart Firefox, then set the preferences listed under Firefox in README.md",
}


def install(args):
    paths = locations()
    manifest = paths["state"] / "current.json"
    if manifest.exists():
        raise RuntimeError("An installation is already recorded. Run uninstall before installing again or changing components.")
    targets = plan(args.component)
    has_firefox = any(target.name == "userChrome.css" for target, _ in targets)
    for target, source in targets:
        if not exists(source):
            raise RuntimeError(f"Missing bundled file: {source}")
        if source.is_file() and target.is_dir() and not target.is_symlink():
            raise RuntimeError(f"Expected a file, found a directory: {target}")
    if args.component == "all" and not has_firefox:
        print("Skip firefox: no Firefox profile found.")
    for target, _ in targets:
        print(f"{'Replace (back up first)' if exists(target) else 'Create'}: {target}")
    if args.dry_run:
        print("Dry run: nothing changed.")
        return
    paths["state"].mkdir(parents=True, exist_ok=True)
    os.chmod(paths["state"], 0o700)
    backups = paths["state"] / "backups"
    backups.mkdir(exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="install-", dir=backups))
    records = []
    try:
        for index, (target, _) in enumerate(targets):
            saved = backup / str(index) if exists(target) else None
            if saved is not None:
                copy(target, saved)
            records.append({"target": str(target), "backup": str(saved) if saved is not None else None})
    except BaseException:
        shutil.rmtree(backup)
        raise
    state = {"component": args.component, "files": records,
             "status": "installing", "backup": str(backup)}
    write_json(manifest, state)
    try:
        for target, source in targets:
            remove(target)  # Replace symlinks themselves, never write through them.
            copy(source, target)
        state["status"] = "installed"
        write_json(manifest, state)
    except BaseException:
        restore_files(records)
        manifest.unlink(missing_ok=True)
        raise
    print(f"Installed {args.component}. Backups: {backup}")
    print("Apply it:")
    for name in COMPONENTS:
        if args.component in (name, "all") and not (name == "firefox" and not has_firefox):
            print(f"  {name}: {APPLY_HINTS[name]}")
    if args.component in ("plasma", "all"):
        print("  Kate/KWrite editor colors: select OLED under Settings → Editor → Fonts & Colors.")


def uninstall(args):
    paths = locations()
    manifest = paths["state"] / "current.json"
    if not manifest.exists():
        raise RuntimeError("No recorded installation found for these HOME/XDG paths.")
    state = json.loads(manifest.read_text(encoding="utf-8"))
    records = state.get("files")
    if not isinstance(records, list) or not records:
        raise RuntimeError("Install record is damaged: no files recorded.")
    # The recorded paths are authoritative. The Firefox default profile
    # may have changed since installation, so do not recompute them.
    for record in records:
        if record.get("backup") and not exists(Path(record["backup"])):
            raise RuntimeError(f"Missing backup; nothing restored: {record['backup']}")
        print(f"Restore previous contents (or remove newly created path): {record['target']}")
    if args.dry_run:
        print("Dry run: nothing changed.")
        return
    recovery_root = paths["state"] / "recovered"
    recovery_root.mkdir(exist_ok=True)
    recovery = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-"), dir=recovery_root))
    restore_files(records, recovery)
    write_json(paths["state"] / "last-uninstall.json", {**state, "recovery": str(recovery)})
    manifest.unlink()
    print(f"Previous files restored. Your installed files and any edits were saved in: {recovery}")
    component = state.get("component", "")
    if component in ("plasma", "all"):
        print("If OLED is still selected as your Global Theme or color scheme, "
              "choose another one in System Settings now.")
    if component in ("firefox", "all"):
        print("Restart Firefox to drop the removed stylesheets.")


def main():
    parser = argparse.ArgumentParser(description="OLED KDE: per-user installation with backups; never use sudo.")
    sub = parser.add_subparsers(dest="action", required=True)
    add = sub.add_parser("install", help="Back up current files, then install the requested components")
    add.add_argument("--component", choices=("all",) + COMPONENTS, default="all")
    add.add_argument("--dry-run", action="store_true")
    undo = sub.add_parser("uninstall", help="Restore files recorded by install")
    undo.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Run as your regular desktop user, without sudo.")
    try:
        (install if args.action == "install" else uninstall)(args)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
