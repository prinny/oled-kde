"""Generator tests: committed artifacts must match the palette."""

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("oled_kde_generate", ROOT / "generate.py")
generate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate)


class GenerateTests(unittest.TestCase):
    def test_committed_artifacts_are_up_to_date(self):
        for relative, text in generate.artifacts().items():
            self.assertEqual((ROOT / relative).read_text(encoding="utf-8"), text,
                             f"{relative} is stale; run python3 generate.py")

    def test_artifact_list(self):
        self.assertEqual(set(generate.artifacts()), {
            "color-schemes/OLED.colors",
            "plasma/desktoptheme/oled/colors",
            "konsole/OLED.colorscheme",
            "konsole/OLED.profile",
            "ghostty/oled",
            "editors/oled.lua",
            "editors/oled.toml",
            "editors/oled.theme",
            "kate/OLED.theme",
            "firefox/userChrome.css",
            "firefox/userContent.css",
            "firefox/darkreader-oled-settings.json",
        })

    def test_palette_lands_in_artifacts(self):
        artifacts = generate.artifacts()
        self.assertIn("[Colors:Window]\nBackgroundAlternate=22,22,22\nBackgroundNormal=0,0,0",
                      artifacts["color-schemes/OLED.colors"])
        for i, color in enumerate(generate.ANSI):
            self.assertIn(f"palette = {i}=#{color}", artifacts["ghostty/oled"])
        kate = json.loads(artifacts["kate/OLED.theme"])
        self.assertEqual(kate["metadata"]["name"], "OLED")
        self.assertEqual(kate["editor-colors"]["BackgroundColor"], "#000000")
        self.assertEqual(kate["text-styles"]["String"]["text-color"], "#" + generate.POSITIVE)
        self.assertEqual(kate["text-styles"]["Keyword"]["text-color"], "#" + generate.VISITED)
        dark_reader = json.loads(artifacts["firefox/darkreader-oled-settings.json"])
        self.assertEqual(dark_reader["theme"]["darkSchemeBackgroundColor"], "#000000")
        self.assertIn('background = #000000', artifacts["ghostty/oled"])


if __name__ == "__main__":
    unittest.main()
