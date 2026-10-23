# Botanical depth collage — design, sources and verification

The user requested **three-dimensional botanical photo compositions** with overlapping real images, foreground reeds, generous lighting and restrained interactive depth, not a stock-template carousel.

## Open-source architecture

- [Atropos](https://github.com/nolimits4web/atropos) 2.x, MIT © Vladimir Kharlampidi. The real vendor source is at `vendor/atropos/atropos.mjs` and its SCSS structural rules were converted to `vendor/atropos/atropos.css`. Original MIT terms are preserved at `vendor/atropos/LICENSE`.
- `src/botanical-depth.mjs` initializes the actual Atropos parallax library for separate hero and story scenes. CSS transforms each nested layer based on `data-atropos-offset` (background rings, photo frames, photo detail, specimen and foreground reeds).
- `botanical-depth.css` defines responsive positions, illumination, photo clipping, shadows, editorial typography and depth separation. It is loaded after the earlier site, grid and motion styles so existing pages remain functional.
- `assets/illustrated-reeds.svg` is a new, locally-authored layered botanical illustration. It has multiple reed stems, tapered leaf forms and warm ochre seed heads. It is artwork, **not a scientifically identified field specimen from Iraq**.

## Photography and provenance

1. Hero Iraqi wetland photograph, *Marshes in southern Iraq.jpeg* — author **Almendilawi**, licensed **CC BY-SA 4.0**, source https://commons.wikimedia.org/wiki/File:Marshes_in_southern_Iraq.jpeg . Cropped within an organic photo frame.
2. Secondary Iraqi marsh photograph, *Marshes - South iraq.jpg* — source https://commons.wikimedia.org/wiki/File:Marshes_-_South_iraq.jpg . The existing site credited Wikimedia Commons under CC BY-SA 4.0; verify author and exact license at the source before redistribution.
3. Vintage botanical plate, *494 Typha angustifolia.jpg* — **Carl Axel Magnus Lindman** (1856–1928), public domain, source https://commons.wikimedia.org/wiki/File:494_Typha_angustifolia.jpg . Its subject is Typha angustifolia, not a documented photo of Iraq's marsh plants. The image is used as editorial background research imagery, not as data or species verification.

The photos and botanical plate are currently requested from Wikimedia Commons at runtime; other internal assets and JS/CSS are shipped from the repository. Any downstream redistribution of transformed CC BY-SA photography must satisfy the source photo's requirements (including appropriate attribution, link, indication of adaptations, and applicable ShareAlike terms).

## Accessibility and performance

- Atropos initializes only on fine-pointer hover-capable devices; coarse pointer, reduced-motion and reduced-data contexts retain a static full-layer arrangement.
- Hover rotation is capped at ±8°; scene content preserves semantic captions and descriptive photographic `alt` text. Reed silhouette and orb highlights have empty alt/hidden semantics.
- No WebGL canvas, video or large reactive state is introduced. Each scene uses existing image assets and one small SVG.
- The study map, model parameters and evidence reporting are **unchanged**.

## Verification

The unit suite checks animation accessibility defaults; Playwright/Chrome verifies both scenes, five or more independent layer depths, real third-party photograph decoding, foreground SVG loading and the interaction state under actual pointer hover. The same run continues to verify narrow-mobile scrolling, working model forms and map click targets. Screenshots are captured by the Scientific Core CI workflow.

**Scientific caveat:** Nothing in these atmospheric photo treatments changes MarshNet V2's currently disappointing water-prediction results or establishes field accuracy.
