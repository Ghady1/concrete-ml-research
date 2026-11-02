# Offline web assets

Reviewed and downloaded for the local Concrete Research Studio redesign on
2026-11-02. All runtime files are local under `web/public/assets/`; none of the
source URLs below is required during the demonstration. The photographs are
editorial material illustrations, not photographs of the project's specimens,
measurements or laboratory. No generated photographs are used.

## Fonts

| Local file | Source and license | Intended use |
|---|---|---|
| `source-sans-3.woff2` | [Adobe Source Sans 3 official release](https://github.com/adobe-fonts/source-sans/tree/release/WOFF2/VF), SIL Open Font License 1.1, Adobe copyright | Body, forms, navigation and tabular numbers; variable upright font. |
| `source-serif-4.woff2` | [Adobe Source Serif 4 official release](https://github.com/adobe-fonts/source-serif/tree/release/WOFF2/VAR), SIL Open Font License 1.1, Adobe copyright | Editorial headings; variable Roman font with optical sizing. |

Original font binaries are unmodified. The complete original license files are
bundled alongside them as `SOURCE-SANS-LICENSE.md` and
`SOURCE-SERIF-LICENSE.md`. Use local `@font-face` URLs, `font-display: swap`,
`font-weight: 200 900`; prefer `font-optical-sizing: auto` for Source Serif 4.
Do not request Google Fonts or any remote font CDN at runtime.

Exact font downloads:

- <https://raw.githubusercontent.com/adobe-fonts/source-sans/release/WOFF2/VF/SourceSans3VF-Upright.otf.woff2>
- <https://raw.githubusercontent.com/adobe-fonts/source-serif/release/WOFF2/VAR/SourceSerif4Variable-Roman.otf.woff2>
- <https://raw.githubusercontent.com/adobe-fonts/source-sans/release/LICENSE.md>
- <https://raw.githubusercontent.com/adobe-fonts/source-serif/release/LICENSE.md>

## Photographs

| Local file | Photographer and original source | License and modifications |
|---|---|---|
| `concrete-architecture.webp` | **Matt Reames**, [white concrete building during daytime, Bellevue](https://unsplash.com/photos/white-concrete-building-during-daytime-U6WuKgCYbKE), published 2018-12-04 | [Unsplash License](https://unsplash.com/license). CDN-resized to 1600 × 1067, encoded WebP at quality 80; no content alteration. |
| `concrete-texture.webp` | **Meg (@megindoors)**, [close-up of a textured concrete surface](https://unsplash.com/photos/close-up-of-a-textured-concrete-surface-y5P_Gh2OZ8E), published 2025-11-04 | [Unsplash License](https://unsplash.com/license). CDN-sized image further resized proportionally to 800 × 533 and re-encoded WebP quality 65 using existing Pillow; no content alteration. |
| `coarse-aggregate.jpg` | **Bill Bradley / Billbeee at English Wikipedia**, [20mm-aggregate.jpg](https://commons.wikimedia.org/wiki/File:20mm-aggregate.jpg), photographed/uploaded 2007-10-24 | Selected license: [Creative Commons Attribution 3.0 Unported](https://creativecommons.org/licenses/by/3.0/). Original 900 × 675 JPEG is unmodified. Attribution, source link and license link must appear in the app's accessible Credits area. |

The aggregate photo is specifically the verified photograph of coarse stones
held in a hand, not the similarly named Commons `Coarse_aggregate.jpg` upload
whose visible contents are sand stockpiles. The latter was inspected and
rejected to avoid misleading the user.

Recommended visible credit text:

> Architecture: Matt Reames / Unsplash. Concrete texture: Meg / Unsplash.
> Aggregate: Bill Bradley (Billbeee), Wikimedia Commons, CC BY 3.0; unmodified.
> Fonts: Adobe Source Sans 3 and Source Serif 4, SIL OFL 1.1.

For the CC BY photograph, keep its author/source/license links together in
Credits. Unsplash attribution is optional under its license but retained as a
courtesy and for provenance. Do not imply that any photographer or institution
endorses this research software.

## Runtime and verification

`credits.json` contains machine-readable credits, exact download URLs, dimensions,
byte sizes and SHA-256 checksums. It can power a Credits page directly. All three
images were decoded and visually inspected. Fonts are official WOFF2 binaries;
no extra asset-processing dependency was installed. Pillow was already present
and used only to reduce the texture payload.

Suggested alt text is included in the JSON. If an image is purely decorative
beside equivalent explanatory text, use empty alt text instead. Do not label the
photographs as the user's laboratory or as simulated model outputs. The three
photos total approximately 321 kB; font binaries total approximately 591 kB.

## Original material companions

The cement sack, coarse-aggregate stone, fine-aggregate sand mound and water
character are original inline SVG artwork in `web/src/material-companion.tsx`.
They are decorative, have no effect on calculations, use no external assets or
runtime requests, and add no dependencies. They are excluded from assistive
technology and printing. Their short settling animation respects both the
studio motion toggle and the operating system reduced-motion preference.
