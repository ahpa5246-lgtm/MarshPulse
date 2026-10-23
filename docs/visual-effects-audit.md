# MarshPulse — Visual depth and illumination audit
23 October 2026 · UI polish v3

## Defects in the previous release

- **Flat surfaces:** cards and lab panels still relied on borders with nearly no depth hierarchy.
- **Monochromatic green:** greens repeated everywhere without color-role distinction.
- **Unstructured whitespace:** calm reading space was good, but backgrounds did not visually link sections.
- **Weak focus hierarchy:** primary actions and imagery had to read differently from support notes.
- **Missing visual regression gates:** UI checks covered interactions and image loading but not the CSS treatments themselves.

## Design improvements implemented

1. **Atmospheric light:** warm sunshine upper-left, sky-blue and lilac reflections around photography, locally constrained glows behind images, not over text.
2. **Purposeful grid:** 63px hero coordinate lattice, 46px chapter-card grid and 56px introduction grid with fading alpha masks and no interaction.
3. **Elevation system:** reusable soft, raised and focus shadow tokens with a restrained hierarchy; hero photos have more depth than body text.
4. **Semantic palette:** neutral cream/white surface as the primary area, botanical greens as identity, river blue for scientific analysis, lavender for AI, and peach/coral for editorial narrative.
5. **Interactive feedback:** smooth, measurable elevation on hover and focus; no jumping touch cards; clear keyboard outline.
6. **Research discipline:** dark water map retains contrast, while lab controls are lightly raised on a neutral surface.
7. **Accessibility:** reduced-motion support and 320px horizontal reflow checks.

The styling is centralized in visual-effects.css, loaded after previous styles on all four pages. No proprietary Figma components or assets are copied.

## Verification

The browser smoke suite now checks that the visual-effects stylesheet loads, the hero grid exists, key photograph shadows render, all three feature cards use different gradients, the lighting field exists, and the story retains contrast. It also tests actual image decoding, training/export, data import, 320px overflow and desktop/mobile navigation.

Full-page browser evidence is uploaded as marshpulse-browser-proof on successful Scientific Core CI runs. CSS assertions verify that effects exist; human judgment of their beauty and exact alignment is still necessary.

## Science is unchanged

MarshNet V2's first real Sentinel-2 pilot did not beat persistence. UI refinement does not certify training accuracy, observational labels or physical impact.
