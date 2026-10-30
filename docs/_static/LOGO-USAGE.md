# PyTES logo files

All backgrounds are **transparent**. "light" and "dark" refer to the page theme the logo is meant to sit on.

| File | Use |
|---|---|
| `pytes-logo-light.svg` | Full logo (icon + wordmark) for light or white backgrounds. Text is outlined: no font needed. |
| `pytes-logo-dark.svg` | Same, for dark backgrounds. |
| `pytes-icon-light.svg`, `pytes-icon-dark.svg` | Icon only (4 bars), for avatars and social images. |
| `favicon.svg`, `favicon.ico`, `apple-touch-icon.png` | Same 4-bar icon and light-theme colours as the logo, so favicon and logo match. Readable on light and dark browser tabs. |
| `source/pytes-logo-*-live-text.svg` | Editable versions: the wordmark is live text and needs Space Grotesk installed. Edit these, then re-export outlines (Inkscape: Path > Object to Path). |
| `source/SpaceGrotesk-OFL.txt` | Licence of the typeface (SIL Open Font License 1.1). |

## README snippet (GitHub switches with the reader's theme)

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/_static/pytes-logo-dark.svg">
    <img alt="PyTES" src="docs/_static/pytes-logo-light.svg" width="80%">
  </picture>
</p>
```

## Palette

| Role | Light theme | Dark theme |
|---|---|---|
| Bars, bottom to top | `#C2410C` `#E8590C` `#FF922B` `#FFC078` | `#D9480F` `#F76707` `#FFA94D` `#FFD8A8` |
| "Py" | `#E8590C` | `#FF922B` |
| "TES" | `#3A1A0A` | `#FFF1E0` |

## Plot colours

Figures use their own palette, chosen for readability with colour-vision deficiency (DESIGN
D15). It shares the brand orange.

| Role | Colours |
|---|---|
| Line colour cycle "PyTES Thermal", in order, for light backgrounds (style `pytes.thermal`) | `#E8590C` `#1F4E9C` `#14A08A` `#F0A930` `#A23B72` `#88C7F0` `#36312E` |
| Line colour cycle "PyTES Thermal (dark)", in order, for dark backgrounds (style `pytes.thermal_dark`) | `#F76707` `#6785F9` `#04B68B` `#FFC66C` `#B06C99` `#B2D5F8` `#D9D0C7` |
| Sequential colourmap "ember" | dark brown `#35130E`, through `#E8590C`, to cream `#FFEFD6` (256 values in `src/pytes/colourmaps/ember.csv`; matplotlib name `pytes.ember`) |
| Diverging colourmap "thaw" | dark navy `#11198C`, through `#1F4E9C`, to near-white `#F1EDED`, through `#E8590C`, to dark red-brown `#4C160E` (256 values in `src/pytes/colourmaps/thaw.csv`; matplotlib name `pytes.thaw`) |

## Notes

- The flame outline comes from the SVG Repo "flame-danger" icon (CC0, per the maintainer). The bars, colours and wordmark are new.
- Keep the editable `source/` files in the repo so the logo can be changed later.
