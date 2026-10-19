"""Configuration lifecycle tests. Never reads or writes real desktop settings."""

import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("oled_kde_theme", Path(__file__).resolve().parents[1] / "theme.py")
theme = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(theme)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="oled kde test ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / "config with spaces"),
            "XDG_DATA_HOME": str(self.home / "data"),
            "XDG_STATE_HOME": str(self.home / "state"),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.make_firefox_profile()

    def make_firefox_profile(self):
        base = theme.locations()["config"] / "mozilla/firefox"
        (base / "abc123.default-release").mkdir(parents=True)
        (base / "profiles.ini").write_text(
            "[Install4F96D1932A9F858E]\nDefault=abc123.default-release\nLocked=1\n\n"
            "[Profile0]\nName=default-release\nIsRelative=1\n"
            "Path=abc123.default-release\nDefault=1\n", encoding="utf-8")
        return base / "abc123.default-release"

    def install(self, component="all", dry=False):
        theme.install(argparse.Namespace(component=component, dry_run=dry))

    def uninstall(self, dry=False):
        theme.uninstall(argparse.Namespace(dry_run=dry))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def tree(self):
        return {str(p.relative_to(self.home)) for p in self.home.rglob("*")}

    def test_fresh_install_and_restore(self):
        targets = [p for p, _ in theme.plan("all")]
        self.install()
        self.assertTrue(all(theme.exists(p) for p in targets))
        colors = theme.locations()["data"] / "color-schemes/OLED.colors"
        self.assertIn("ColorScheme=OLED", colors.read_text())
        profile = theme.firefox_profile()
        self.assertIn("#000000", (profile / "chrome/userChrome.css").read_text())
        self.uninstall()
        self.assertTrue(all(not theme.exists(p) for p in targets))
        self.assertFalse((theme.locations()["state"] / "current.json").exists())

    def test_existing_files_and_directories_restored(self):
        for target, source in theme.plan("all"):
            self.write(target / "old.txt" if source.is_dir() else target, "original contents")
        unrelated = theme.locations()["data"] / "konsole/MyProfile.profile"
        self.write(unrelated, "leave this alone")
        self.install()
        self.uninstall()
        for target, source in theme.plan("all"):
            self.assertEqual((target / "old.txt" if source.is_dir() else target).read_text(),
                             "original contents")
        self.assertEqual(unrelated.read_text(), "leave this alone")

    def test_symlink_restored_without_changing_external_target(self):
        external = self.home / "external.css"
        self.write(external, "external original")
        chrome = theme.firefox_profile() / "chrome/userChrome.css"
        chrome.parent.mkdir(parents=True)
        chrome.symlink_to(external)
        self.install("firefox")
        self.assertFalse(chrome.is_symlink())
        self.assertEqual(external.read_text(), "external original")
        self.uninstall()
        self.assertTrue(chrome.is_symlink())
        self.assertEqual(chrome.readlink(), external)

    def test_dry_run_creates_nothing(self):
        before = self.tree()
        self.install(dry=True)
        self.assertEqual(self.tree(), before)

    def test_component_selection(self):
        self.install("ghostty")
        self.assertTrue((theme.locations()["config"] / "ghostty/themes/oled").exists())
        self.assertFalse((theme.locations()["data"] / "konsole").exists())
        self.assertFalse((theme.locations()["data"] / "color-schemes").exists())
        self.uninstall()
        self.install("konsole")
        self.assertFalse((theme.locations()["config"] / "ghostty/themes/oled").exists())
        self.assertTrue((theme.locations()["data"] / "konsole/OLED.profile").exists())

    def test_second_install_refused(self):
        self.install("plasma")
        colors = theme.locations()["data"] / "color-schemes/OLED.colors"
        before = colors.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "already recorded"):
            self.install("plasma")
        self.assertEqual(colors.read_bytes(), before)

    def test_edits_saved_during_uninstall(self):
        chrome = theme.firefox_profile() / "chrome/userChrome.css"
        self.write(chrome, "previous CSS")
        self.install("firefox")
        chrome.write_text("my new edits")
        self.uninstall()
        self.assertEqual(chrome.read_text(), "previous CSS")
        recovered = list((theme.locations()["state"] / "recovered").rglob("userChrome.css"))
        self.assertTrue(any(p.read_text() == "my new edits" for p in recovered))

    def test_uninstall_dry_run_keeps_installation(self):
        self.install("konsole")
        self.uninstall(dry=True)
        self.assertTrue((theme.locations()["data"] / "konsole/OLED.colorscheme").exists())
        self.assertTrue((theme.locations()["state"] / "current.json").exists())

    def test_install_failure_rolls_back(self):
        colors = theme.locations()["data"] / "color-schemes/OLED.colors"
        self.write(colors, "previous scheme")
        real_copy = theme.copy

        def failing_copy(source, target):
            if source == theme.SOURCE / "konsole/OLED.profile":
                raise OSError("simulated disk failure")
            return real_copy(source, target)

        with patch.object(theme, "copy", side_effect=failing_copy):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.install("all")
        self.assertEqual(colors.read_text(), "previous scheme")
        self.assertFalse((theme.locations()["state"] / "current.json").exists())

    def test_missing_backup_refuses_uninstall_before_removal(self):
        colors = theme.locations()["data"] / "color-schemes/OLED.colors"
        self.write(colors, "previous scheme")
        self.install("plasma")
        manifest = theme.locations()["state"] / "current.json"
        state = json.loads(manifest.read_text())
        for record in state["files"]:
            if record["backup"]:
                theme.remove(Path(record["backup"]))
        with self.assertRaisesRegex(RuntimeError, "Missing backup"):
            self.uninstall()
        self.assertIn("ColorScheme=OLED", colors.read_text())

    def test_missing_firefox_profile_fails_before_file_changes(self):
        theme.remove(theme.locations()["config"] / "mozilla")
        before = self.tree()
        with self.assertRaisesRegex(RuntimeError, "No Firefox profile"):
            self.install("firefox")
        self.assertEqual(self.tree(), before)
        self.install("plasma")  # Other components do not need Firefox.

    def test_all_skips_missing_firefox_and_still_uninstalls(self):
        theme.remove(theme.locations()["config"] / "mozilla")
        self.install("all")
        self.assertTrue((theme.locations()["data"] / "konsole/OLED.profile").exists())
        self.make_firefox_profile()  # A profile appearing later must not block uninstall.
        self.uninstall()
        self.assertFalse((theme.locations()["data"] / "konsole/OLED.profile").exists())

    def test_uninstall_after_default_profile_changes(self):
        first = theme.firefox_profile() / "chrome/userChrome.css"
        self.install("firefox")
        self.assertTrue(first.exists())
        base = theme.locations()["config"] / "mozilla/firefox"
        (base / "xyz.default-release").mkdir()
        (base / "profiles.ini").write_text(
            "[Profile0]\nName=new default\nIsRelative=1\nPath=xyz.default-release\nDefault=1\n",
            encoding="utf-8")
        self.uninstall()
        self.assertFalse(first.exists())

    def test_malformed_profiles_ini_counts_as_no_profile(self):
        base = theme.locations()["config"] / "mozilla/firefox"
        (base / "profiles.ini").write_text("this is not an ini file [[\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "No Firefox profile"):
            self.install("firefox")
        self.install("all")  # Skips Firefox instead of crashing.

    def test_firefox_profile_from_profile_section(self):
        base = theme.locations()["config"] / "mozilla/firefox"
        (base / "profiles.ini").write_text(
            "[Profile1]\nName=other\nIsRelative=1\nPath=other.default\n\n"
            "[Profile0]\nName=main\nIsRelative=1\nPath=abc123.default-release\nDefault=1\n",
            encoding="utf-8")
        self.assertEqual(theme.firefox_profile(), base / "abc123.default-release")


if __name__ == "__main__":
    unittest.main()
