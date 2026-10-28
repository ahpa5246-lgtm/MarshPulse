# MarshPulse — customer-facing historical screening workspace (MVP)

This is a **working client-side prototype** shipped as `business.html`; it is **not** a commercial subscription platform or a scientifically certified monitoring service.

## Delivered
- Honest historical monitoring of the existing Sentinel-2 Hawizeh **pilot rectangle only** (not an official marsh boundary), with an explicit observation range.
- Adjustable two-endpoint surface-water-proxy comparison, with coverage and index interpretation.
- Review flags for substantial negative **matched-pixel** month-over-month proxy changes, only when **both** adjacent months pass a user-selected valid-pixel threshold. Low-coverage months are shown separately.
- Human-readable print / Save-as-PDF report, exact CSV subset, and machine-readable JSON bundle containing source, quality, flags, months, and caveats.
- Shareable **settings-only** URL for the built-in dataset; saved local browser preferences, not a user account.
- File upload for **user-supplied source-format JSON** from a separate satellite analysis, with bounding box, date, quality and schema validation. An uploaded label is not independent proof of origin. No server upload, data sync or persistent file store.

## What is not delivered
No payment gateway, subscription, accounts, tenancy or customer database. No automated email/SMS notifications, live polling or public drought alerts. No arbitrary AOI measurement from a drawn polygon: uploaded records must already be processed upstream. No commercial SLA or verified ecological decisions, and no claim of water savings. Do not advertise flagged decreases as confirmed drought: spectral proxies can be affected by clouds, reeds and classification errors.

## Working with new client geographies
1. Obtain permission and an appropriately licensed Sentinel-2/other satellite dataset.
2. Run a transparent AOI-specific image-analysis pipeline independently; retain scene IDs, QA, spatial resolution, complete period, and matching pixel footprint.
3. Publish an observation JSON conforming to `marshpulse-observed-water-v1`: `format`, `label=UNVERIFIED SATELLITE PROXY`, `official_wetland_boundary=false`, `bbox=[west,south,east,north]`, `imagery`, and sorted unique monthly `rows=[[YYYY-MM,waterProxyKm2,validPixelFraction,matchedPixelDeltaKm2|null]]` (at least 24 months).
4. Upload that JSON in the browser and screen results; seek independent field reference before ecological or investment decisions. Exports disclose the unverified state.

## Next commercial backend increments (not yet implemented)
- A server-mediated area-processing queue and monthly Earth observation refresh; explicit measurement-status UI.
- Authenticated organizations, private AOI ownership, encrypted customer data, audit trail, rate limiting and usage metering.
- Tenant-isolated scheduled reports, verified notification delivery with customer consent and unsubscribe.
- Billable report orders and subscriptions behind an established payment provider, proper invoicing, support and SLA.
- Independent QA for commercial use and multi-region training/testing with reference observations.

## Acceptance
`node --test tests/business-core.test.mjs` tests the actual archive, provenance, adverse cloud conditions and exports. `node --test tests/*.test.mjs` runs all JavaScript unit tests. Open `business.html` through a local HTTP server or GitHub Pages, never a bare `file://` URL because it fetches JSON.
