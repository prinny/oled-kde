# OLED KDE

Pure-black color scheme and Plasma style for KDE Plasma 6, with matching terminal, editor, and Firefox themes.

This is a port of [oled-gnome](https://github.com/drkhn1234/oled-gnome) (MIT) to KDE Plasma. The palette, the terminal ANSI colors, and the installer's backup/restore design come from that project; see [Credits and license](#credits-and-license). Like the original, this port recolors the stock styling — Breeze widget style, Breeze window decoration, and the default Plasma theme elements — and changes no layout or geometry. No system-file replacement is needed.

The components are independent. You can install any subset: the Plasma theme alone, only a terminal theme, or everything.

## Compatibility

| Component | Tested on | Other versions |
| --- | --- | --- |
| KDE Plasma (color scheme, Plasma style, Global Theme) | Plasma 6.7.5, Breeze style/decoration | Untested; Plasma 5 is not supported |
| Konsole | 26.08.1 | Color schemes are plain config files; should work on older Konsole |
| Ghostty | 1.3.1 | Theme format is stable; older releases untested |
| Firefox (`userChrome.css`/`userContent.css`) | 158.0 | Untested; CSS variable names can change between releases |
| Neovim | 0.12.5 | Uses only `nvim_set_hl`; 0.8+ expected to work |
| Helix, btop | Not run (file formats validated only) | Untested |
| Kate/KWrite (`OLED.theme`) | KSyntaxHighlighting as shipped with Plasma 6.7.5 | Other versions untested |

## Requirements

- **Python 3** (standard library only), for `theme.py`, the installer. No other tools, no network access, and no `sudo` are needed.
- **plasma** component: KDE Plasma 6 with the stock Breeze widget style and window decoration. The Kate/KWrite editor theme is installed with this component.
- **konsole**, **ghostty**, **editors** (Neovim, Helix, btop), and **firefox** components: only the application named by each component. Installing a component for an application you don't have just leaves an unused theme file, which uninstall removes again. The `all` component skips Firefox (with a note) when no Firefox profile is found; `--component firefox` reports an error instead.
- Firefox web-page theming additionally needs the optional **Dark Reader** add-on, installed manually as described under [Firefox](#firefox). The installer downloads nothing.

## Quick start: all components

Clone or download this repository, extract it if needed, and open a terminal in the `oled-kde` folder. Then:

1. Preview the changes:

```sh
python3 theme.py install --dry-run
```

2. Install:

```sh
python3 theme.py install
```

Run as your regular desktop user, **without sudo**. The helper backs up the paths it replaces and writes an install record before changing anything. It refuses a second install until you uninstall the first one, so backups are not silently stacked or replaced.

3. Apply the themes. The installer only copies files and prints these steps:

```sh
plasma-apply-lookandfeel -a io.local.oled.desktop
```

That selects the OLED Global Theme (color scheme + Plasma style + Breeze) and keeps your desktop layout — layout is only reset if you pass `--resetLayout`, which you should not. Selecting **OLED** under **System Settings → Global Theme** does the same thing. To apply only the application colors instead, run `plasma-apply-colorscheme OLED`. Then select the theme by name in each application: the **OLED** profile or color scheme in Konsole, `theme = oled` in Ghostty's config, `colorscheme oled` in Neovim, `theme = "oled"` in Helix, the `oled` color theme in btop's options, and **OLED** under **Settings → Editor → Fonts & Colors** in Kate/KWrite. Firefox (when a profile was found) needs a restart plus the preferences under [Firefox](#firefox).

Icons, cursors, sounds, splash screen, and wallpaper are not part of this package and are left exactly as they are.

## Install just one component

```sh
python3 theme.py install --component plasma
```

Components: `plasma`, `konsole`, `ghostty`, `editors`, `firefox`, and `all` (the default). The `editors` component installs the Neovim, Helix, and btop themes together; the Kate/KWrite theme is part of `plasma`.

## What gets installed

The default paths below follow the XDG directory variables if you have customized them.

| Path | Purpose |
| --- | --- |
| `~/.local/share/color-schemes/OLED.colors` | Qt Widgets/Kirigami application colors, window decoration colors |
| `~/.local/share/plasma/desktoptheme/oled/` | Plasma style colors (panel, menus, notifications); graphics come from the default Plasma theme |
| `~/.local/share/plasma/look-and-feel/io.local.oled.desktop/` | Global Theme selecting the two packages above plus Breeze |
| `~/.local/share/org.kde.syntax-highlighting/themes/OLED.theme` | Kate/KWrite editor text colors |
| `~/.local/share/konsole/OLED.colorscheme`, `OLED.profile` | Konsole colors and a ready-made profile |
| `~/.config/ghostty/themes/oled` | Ghostty theme (`theme = oled`) |
| `~/.config/nvim/colors/oled.lua` | Neovim colorscheme |
| `~/.config/helix/themes/oled.toml` | Helix theme |
| `~/.config/btop/themes/oled.theme` | btop theme |
| `<Firefox profile>/chrome/userChrome.css`, `userContent.css` | Firefox chrome and `about:` pages; the profile is found via `profiles.ini` |
| `~/.local/state/oled-kde/` | Install record, original files, and recovery copies |

Files already at these paths are **backed up and replaced** — most importantly, an existing Firefox `userChrome.css` is saved before it is overwritten, not merged. The two Plasma package directories are replaced as a whole, so any extra files inside them are backed up along with them and restored on uninstall. Files elsewhere are left alone. Existing symlinks at the replaced paths are saved and restored as symlinks; the installer does not write through those links.

## Remove it and restore your setup

Keep the extracted folder and run:

```sh
python3 theme.py uninstall --dry-run
python3 theme.py uninstall
```

Use the same desktop user and XDG directory variables as during installation. The helper restores the backed-up files and removes paths that it newly created. The currently installed files — including any edits you made — are saved under `~/.local/state/oled-kde/recovered/` before restoration. Original backups are retained too.

Uninstall does not change desktop settings. If OLED is still selected as your Global Theme or color scheme, choose another one in System Settings afterwards, and deselect the theme in any terminal or editor where you enabled it. Restart Firefox so it drops the removed stylesheets (and remove the preferences below from `about:config` if you no longer want them).

Do not delete the state directory before uninstalling: it contains your originals. If an install is interrupted, run uninstall to restore the originals before trying again.

## Colors and customization

| Role | Value | Source in oled-gnome |
| --- | --- | --- |
| Backgrounds | `#000000` | every `*_bg_color`, Shell surfaces |
| Foreground | `#FFFFFF` | every `*_fg_color` |
| Button/elevated | `#161616` | Shell unchecked toggles |
| Borders/pressed | `#242424` | Shell border color |
| Hover | `#1A1A1A` | Shell inactive hover |
| Alt rows | `#121212` | GTK 4 surfaces |
| Inactive foreground | `#999999` | GTK 3 insensitive |
| Negative | `#F48771` | destructive/error |
| Terminal ANSI | 16 colors | `palettes/ptyxis/OLED.palette`, verbatim |

Where the GNOME source has no value:

- **Accent** — the source follows the system accent dynamically. In a Plasma session, your accent from **System Settings → Colors & Themes** likewise overrides selection and decoration colors. The files carry `#22D3EE` as a static fallback for places that need a fixed value (non-Plasma Qt, Firefox, editors).
- **Positive/neutral** — `#8AE234` / `#FCE94F` (Ptyxis bright green/yellow), used with conventional semantics.
- **Visited** — `#AD7FA8` (Ptyxis bright magenta).
- **Buttons** — `#161616`, not `#000000`. Breeze derives button frames from contrast, so black-on-black would erase their outlines.

All editor themes share one syntax mapping: keywords violet, strings green, types blue, numbers yellow, comments gray, errors `#F48771`.

To change any color, edit the palette in [`generate.py`](generate.py), run `python3 generate.py`, and reinstall (uninstall first). Restart applications after reinstalling.

## Firefox

The `firefox` component copies two stylesheets into your default profile, found under `~/.config/mozilla/firefox` (or `$XDG_CONFIG_HOME`) or `~/.mozilla/firefox`. Snap and Flatpak builds keep profiles elsewhere and are not detected; copy the two stylesheets into that profile's `chrome/` folder manually. The stylesheets are: `chrome/userChrome.css` (tabs, toolbars, urlbar, panels, sidebar) and `chrome/userContent.css` (`about:` pages, including the new tab page). Firefox only loads them after you set these preferences in `about:config` and restart:

| Preference | Value |
| --- | --- |
| `toolkit.legacyUserProfileCustomizations.stylesheets` | `true` |
| `browser.theme.toolbar-theme` | `0` (dark) |
| `browser.theme.content-theme` | `0` (dark) |
| `devtools.theme` | `dark` |

Web pages keep their own colors. For pure-black web pages, install the [Dark Reader](https://addons.mozilla.org/firefox/addon/darkreader/) add-on from addons.mozilla.org, then import the included settings: **Dark Reader → Settings → Manage settings → Import** and choose [`firefox/darkreader-oled-settings.json`](firefox/darkreader-oled-settings.json). That enables its dynamic engine on all sites with background `#000000`, text `#ffffff`, and selection/scrollbar `#242424`. Dark Reader's own toggles undo this per site or globally (`Alt+Shift+A` / `Alt+Shift+D` by default).

## Known limits

- **GTK 3/4 and libadwaita applications** are not covered by this package. Install [oled-gnome](https://github.com/drkhn1234/oled-gnome) alongside it if you want them black too; its per-user GTK CSS also applies inside a Plasma session.
- **Qt Flatpaks** use their runtime's style and keep their built-in dark look, not `#000000`.
- **Login (SDDM) and system-wide theming** are out of scope for a per-user package. The splash screen keeps whatever your previous setup used.
- **Wallpaper** is not changed. Set a solid black wallpaper in Plasma if you want a true-black desktop.

## Development

[`generate.py`](generate.py) is the single source of truth for colors. It regenerates every artifact it owns (the color schemes, Konsole/Ghostty files, editor themes, Firefox CSS, and the Dark Reader settings) using only the Python standard library, with no files read from outside the repository:

```sh
python3 generate.py
```

The generated artifacts are committed, so installers don't need the generator. Package metadata (`metadata.json`, `plasmarc`, `contents/defaults`) and the Global Theme preview images are not generated; they are maintained by hand.

Run the tests (they use a temporary home directory and never touch real desktop settings):

```sh
python3 -m unittest discover -s tests
```

## Credits and license

OLED KDE is a port of [oled-gnome](https://github.com/drkhn1234/oled-gnome) by its contributors. From that project come the pure-black palette, the Ptyxis ANSI colors (used verbatim for Konsole and Ghostty), and the structure of [`theme.py`](theme.py) (per-user install with backups, an install record, `--dry-run`, and component selection). The editor themes' highlight layouts were adapted from the NoxForge Obsidian themes.

Everything is distributed under the MIT License; see [`LICENSE`](LICENSE), which retains the upstream copyright notices.
