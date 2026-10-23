# Floating Navigation — Headroom + Gumshoe

Implemented October 2026 in MarshPulse on all four public pages: homepage, water laboratory, MarshNet training and research methodology.

## Real open-source building blocks

- **Headroom.js v0.12.0**, Nick Williams — MIT, original source https://github.com/WickyNilliams/headroom.js , locally bundled at `vendor/headroom/*.mjs` with unmodified license `vendor/headroom/LICENSE`. Rewrites consist of adding explicit relative .mjs extensions for native browser imports. Headroom handles user scroll **direction and distance** before the dock is revealed or dismissed.
- **Gumshoe v5.1.2**, Chris Ferdinandi / Go Make Things — MIT, original source https://github.com/cferdinandi/gumshoe , locally bundled at `vendor/gumshoe/gumshoe.min.js` with `vendor/gumshoe/LICENSE.md`. Gumshoe tracks the actively visible chapter of each page and highlights its matching chapter marker. Reflow support is enabled.
- Original local UI code lives in `src/floating-nav.mjs` and `floating-nav.css`. No CDN or npm build is required.

## User experience

1. The main header is unchanged and works even without JavaScript. **The floating dock is supplementary** and not visible above the hero.
2. When someone navigates deeper into a page and **scrolls up**, Headroom reveals a luminous, lightly blurred capsule. It slides out on deliberate downward scrolling to preserve reading space.
3. Four always-labeled destinations (Home / Lab / MarshNet / Methods) show their page icon and current-page state. A desktop badge is included as a shortcut to Home.
4. On desktop, an accessible second-level chapter navigation has clickable section dots and a current chapter label. Gumshoe updates this based on content. The chapter anchors use stable IDs, preserving existing lab links.
5. A thin colored line shows approximate overall page-scroll progress and a visible **back-to-top** control links directly to the first section.
6. On small touch screens, the same information compresses into a safe-area-aware bottom dock with four full route links plus chapter dots; no crucial controls are hidden.
7. While inputs/selects/textarea fields are focused, the dock is temporarily hidden so that it cannot cover model-training or lab controls.

## Performance and accessibility

- Both third-party libraries are locally vendored and MIT-licensed. No HTTP request for fonts, APIs, analytics or navigation assets is needed for the dock.
- Scroll progress updates are throttled by a single `requestAnimationFrame` callback. No polling or forced synchronous layout loops are used.
- The UI is RTL, keyboard-focusable, high-contrast, and uses `aria-current="page"`, Arabic labels, visible focus outlines, standard anchor navigation and a separate chapter list.
- `prefers-reduced-motion` disables the transitions; `prefers-reduced-transparency` makes the capsule opaque. Mobile pages leave footer breathing room.
- No script hijacks standard links or scroll-wheel behavior.

## Verification and scope

The Node unit tests cover route names, chapter uniqueness, bounded progress and safe no-DOM behavior. Real Chrome browser smoke checks the loaded dock, direction-aware reveal, active Gumshoe chapter, progress, mobile dimensions and reflow down to 320px while continuing to exercise the existing lab and M1 neural network. These tests check function and layout, not an independent WCAG audit.

Navigation work is **visual/interaction only**. No changes to the underlying satellite data, MarshNet scientific results or claims of real-world restoration efficacy.
