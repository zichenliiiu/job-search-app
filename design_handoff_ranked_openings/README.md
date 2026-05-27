# Handoff: Ranked Openings (Apt)

## Overview

**Apt** is a job-opening surfacing and ranking tool. It crawls listings across the web, scores them against your background and preferences, and tells you which openings are worth applying to. This handoff covers the **Ranked Openings** view — the primary product surface, a single-user feed of bucketed daily openings.

The app currently assumes one user (no auth flows, no team accounts). The Ranked Openings page is the home/feed screen.

## About the design files

The files in this bundle are **design references created in HTML/JSX** — a working prototype that demonstrates the intended look, interactions, and behavior. They are **not production code to ship as-is**. The expectation is to **recreate this design in the target codebase** (React, Vue, SwiftUI, etc.) using its established patterns, routing, data layer, and component library. If no environment exists yet, pick the framework that best fits the rest of the product (React + Vite or Next.js is a natural starting point given the JSX prototype).

The design tokens in `design-system/colors_and_type.css` should be ported to the target codebase verbatim — these are the source of truth for color, type, spacing, radii, shadows, and motion. The JSX components are illustrative; you'll likely replace them with idiomatic components in your framework.

## Fidelity

**High-fidelity.** Colors, typography, spacing, copy, and interactions are final. The developer should recreate the UI pixel-perfectly. Imagery (company logos) is intentionally absent — see "Open questions" below.

---

## Screens / Views

### 1. Ranked Openings (the only screen in this handoff)

**Purpose.** The user lands here every morning. They scan the day's openings — bucketed by tier into **Top picks** and **Next best** — and decide which ones to open and apply to. They can mark applications as sent. They can scrub back through previous days.

**Layout.**

```
┌───────────────────────────────────────────────────────────────┐
│  TOPBAR  (sticky, 64px, hairline bottom, warm-paper bg+blur)  │
│  ┌─ apt. wordmark ──────────────── ◀ Today · Wed Mar 12 ▶ ──┐ │
└───────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────┐
│  CONTENT  (max-width 980px, centered, 36/32/96 padding)       │
│                                                               │
│   ┌─ Page header ──────────────────────────────────────┐      │
│   │  3 openings worth a look today.                    │      │
│   │  WED · MAR 12 · UPDATED 14 MIN AGO                 │      │
│   └────────────────────────────────────────────────────┘      │
│                                                               │
│   ●  3 top picks    ●  5 next best        8 openings          │
│   ──────────────────────────────────────────────              │
│                                                               │
│   │ ★ Top picks                                3 openings     │
│   ┌────────────────────────────────────────────────────┐      │
│   │ ━━━━━━━ moss accent ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │      │
│   │ Stripe                                             │      │
│   │ Head of Pricing Strategy                           │      │
│   │ 📍 San Francisco, CA  · Remote OK · $200k–$260k    │      │
│   │ · Today                                            │      │
│   ├────────────────────────────────────────────────────┤      │
│   │ ○ Haven't applied            [↗ Open posting]      │      │
│   └────────────────────────────────────────────────────┘      │
│   ... 2 more cards in Top picks ...                           │
│                                                               │
│   │ ↗ Next best                                5 openings     │
│   ┌────────────────────────────────────────────────────┐      │
│   │ ━━━━━━━ amber accent ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │      │
│   │ ... same card structure ...                        │      │
│   └────────────────────────────────────────────────────┘      │
│   ... 4 more cards in Next best ...                           │
└───────────────────────────────────────────────────────────────┘
```

### Components

#### TopBar

- **Element:** sticky `<header>`, `position: sticky; top: 0; z-index: 5`.
- **Background:** `rgba(250, 248, 243, 0.9)` over `backdrop-filter: blur(10px)`. (Token: `--paper` at 90% opacity.)
- **Border-bottom:** `1px solid var(--line-1)` (`#E8E5DC`).
- **Height:** 64px. **Padding:** `0 32px`. **Gap:** 18px.
- **Left:** `apt.` wordmark — Geist 700 italic at 26px, letter-spacing `-0.04em`. Dot is moss (`#1F6B47`). Preceded by a 26px circular SVG mark: 28px-radius outer circle stroked at 3px in `--ink-1`, with a 9px-radius moss-filled inner dot.
- **Right:** date scrubber pill. See below.

#### Date scrubber

- **Container:** `inline-flex` pill, `height: 34px`, `border-radius: 999px`, `1px solid var(--line-1)`, `background: var(--surface)` (`#FFFFFF`), `overflow: hidden`.
- **Three children:** prev button (left chevron), label, next button (right chevron). Each separated by an internal `1px solid var(--line-1)` border on the label's left/right.
- **Label:** padding `0 14px`, sans 13px / weight 500, ink-1. Calendar icon (Lucide `calendar`, 14px, ink-3) followed by the date label ("Today", "Yesterday", "2 days ago"...), then a faint mono day stamp (`· Wed · Mar 12`, ink-3, mono 11px).
- **Buttons:** 10px horizontal padding, chevron 15px, ink-3. Hover: ink-1 + paper-2 background. The "next day" button is disabled when on Today (today is the rightmost date in the timeline).

#### Page header

- **`h1`:** Geist 600 italic accent, **42px / 1.05 / -0.03em / ink-1**. The leading number is wrapped in `<em>` rendered as `font-style: italic; color: var(--accent); font-weight: 600`.
- **Copy:** `<em>{N}</em> openings worth a look today.` — where N is the count of Top picks.
- **Subtitle:** mono 11px, ink-3, uppercase, letter-spacing `0.08em`. Format: `WED · MAR 12 · UPDATED 14 MIN AGO`. (Today's day-of-week, date, and last-sync timestamp.)
- **Margin:** 22px bottom.

#### Summary / legend row

- **Layout:** flex row, `gap: 22px`, `flex-wrap: wrap`. Below the page header. Hairline `border-bottom: 1px solid var(--line-1)` with 18px bottom padding. Bottom margin 18px.
- **Two legend chips:** each is `inline-flex; gap: 8px; align-items: center`. An 8px circular swatch (moss for top picks, amber for next best) → mono 13px medium number → sans 13px ink-3 label. e.g. `● 3 top picks  ● 5 next best`.
- **Right side (`margin-left: auto`):** mono 11px uppercase ink-3 — `8 openings`. Format: `{total} openings`.

#### Section header

- Each section (Top picks / Next best) is preceded by a header row.
- **Layout:** flex row, `align-items: center`, `gap: 12px`, `padding: 0 4px 14px`.
- **Left:** a 3px wide × 18px tall colored bar (`border-radius: 2px`). Moss for Top picks (`var(--tier-s)`), amber for Next best (`var(--tier-b)`).
- **Icon:** Lucide `star` (Top picks) or `trending-up` (Next best), 16px, tinted to match the bar.
- **Title:** sans 17px / weight 600 / ink-1, letter-spacing `-0.005em`. Sentence case ("Top picks", "Next best").
- **Right (`margin-left: auto`):** count badge — mono 11px uppercase ink-3, `0.08em` tracking. Format: `{N} openings` (singular: `1 opening`).

#### Job card

- **Wrapper:** `<article class="jcard top|next">`. `background: var(--surface)`, `border: 1px solid var(--line-1)`, `border-radius: var(--r-3)` (10px), `overflow: hidden`. No shadow. `transition: border-color 120ms var(--ease-out)`.
- **Hover:** `border-color: var(--line-2)` (`#D6D3C8`). No shadow change, no scale.
- **Accent stripe (default):** a 2px top border applied via `::before`, `position: absolute; left: 0; right: 0; top: 0`. Color: moss for `.top`, amber for `.next`.
- **Card list spacing:** `display: flex; flex-direction: column; gap: 12px;`

##### Card body (`.jc-body`)

- `padding: 18px 22px 14px`. `display: flex; gap: 18px; align-items: flex-start`.
- Single column (no logo, no score):
  - **Company name** — Geist 600, 22px, line-height 1.1, letter-spacing `-0.02em`, ink-1. Upright (not italic).
  - **Role title** — sans 14px / 500 / ink-2, line-height 1.35. 4px top margin.
  - **Meta row** — flex row, `gap: 14px`, `flex-wrap: wrap`. 10px top margin. Contains, in order:
    - Location: Lucide `map-pin` (13px, ink-4) + sans 12px ink-2 text.
    - **Remote OK pill** (conditional): `display: inline-flex; padding: 2px 8px; border-radius: 999px; background: var(--accent-soft); color: var(--accent);` Mono 11px / 500.
    - Salary: mono 12px ink-2, prefixed by a 12px mono `$` (ink-4). e.g. `$ 200k–$260k`. Use proper en-dash (`–`), not hyphen.
    - Posted: Lucide `clock` (13px, ink-4) + mono 12px ink-3. Values: `Today`, `1d ago`, `2d ago`, etc.

##### Card foot (`.jc-foot`)

- `border-top: 1px solid var(--line-1)`. `padding: 10px 22px`. `background: var(--paper)` (the warm cream — sits just inside the white card body, providing a subtle 2-tone footer).
- `display: flex; align-items: center; gap: 12px`.
- **Status toggle (left):** a button that flips between two states:
  - **Unapplied** (default): empty circle icon (Lucide `circle`, 16px, ink-4) + text `Haven't applied` (sans 12.5px / ink-3).
  - **Applied:** filled check-circle icon (Lucide `check-circle`, 16px, moss) + text `Applied` (sans 12.5px / moss).
  - Clicking toggles. Hit area is `padding: 4px 10px 4px 6px; border-radius: 999px;` with `margin-left: -6px` so it visually flush-aligns with the card edge.
  - Hover (unapplied): background `var(--paper-2)`, text `var(--ink-2)`.
  - Hover (applied): background `var(--accent-soft)`.
- **Actions (right, `margin-left: auto`):** one button — **Open posting**.
  - `<a class="btn btn-secondary" href={job.url} target="_blank">` containing Lucide `external-link` (13px) + label.
  - Styling: sans 12.5px / 500, `padding: 6px 12px`, `border-radius: 6px`, `border: 1px solid var(--line-2)`, `background: var(--surface)`, color ink-1.
  - Hover: `background: var(--paper-2); border-color: var(--ink-4)`.

---

## Interactions & Behavior

### Date scrubber

- The scrubber walks a list of past days (today + last N days). Today is index 0.
- **◀ (prev):** moves to an older day (`dateIdx + 1`). Disabled when at the end of history.
- **▶ (next):** moves to a more recent day (`dateIdx - 1`). Disabled when on Today.
- Today's date and the "Updated N min ago" stamp in the page header should pull from the server's last-sync time for the selected day. When scrubbing back, "Updated" should change to something like `Synced 9:14 AM` or similar — we left it as static placeholder.

### "Applied" toggle

- Stored per-opening, per-user. Persists across sessions.
- Toggling is optimistic; on failure, revert and surface a toast.
- No counter is shown elsewhere in this view (the previous sidebar with a Tracking count has been removed).

### Open posting

- Opens `job.url` in a new tab (`target="_blank"`, `rel="noreferrer"`).
- No tracking handshake in this iteration. (Future: log a "viewed posting" event for ranking feedback.)

### Animations

- Card border on hover: 120ms `var(--ease-out)` (`cubic-bezier(0.2, 0.7, 0.2, 1)`).
- Date scrubber button color/background: 120ms `var(--ease-out)`.
- Status toggle: 120ms color + background.
- No spring, no scale, no bounce. The brand voice is "efficient" — motion confirms and gets out of the way.

### Responsive

- Not formally specified for this handoff. The content column is `max-width: 980px`, so it stays readable on tablet. For phone, the meta row should wrap naturally; the scrubber label can drop the mono day stamp. Confirm with design before shipping responsive.

---

## State management

Minimum viable state for this view:

```ts
type Tier = 'S' | 'A' | 'B' | 'C' | 'D';

interface Opening {
  id: string;            // stable opening ID
  tier: Tier;            // determines which bucket
  role: string;          // e.g. "Head of Pricing Strategy"
  co: string;            // e.g. "Stripe"
  loc: string;           // e.g. "San Francisco, CA" or "Remote"
  remote: boolean;       // shows the "Remote OK" pill
  salary: string;        // already-formatted range, e.g. "$200k–$260k"
  posted: string;        // already-formatted relative time, e.g. "Today", "2d ago"
  url: string;           // absolute URL to the live posting
}

interface DayFeed {
  date: string;          // ISO date, e.g. "2026-03-12"
  syncedAt: string;      // ISO timestamp of last sync for that day
  topPicks: Opening[];   // tier S
  nextBest: Opening[];   // tier B (and maybe A — TBD with PM)
}

// Per-user application tracking
type AppliedSet = Set<string>; // opening IDs the user marked as applied
```

**Data fetching:** one fetch per visible day. Cache by date. The "haven't applied / applied" status is its own collection (user-scoped) that the feed cross-references.

**Bucket boundary:** the prototype splits cards by an explicit `topPicks` / `nextBest` array. In production, the bucket comes from `tier`: `S → topPicks`, `B → nextBest`. The cut between buckets, and which tiers belong in each, is a product decision worth confirming.

---

## Design tokens

All tokens are defined in `design-system/colors_and_type.css`. Port these to your codebase verbatim.

### Color

| Token | Hex | Used for |
|---|---|---|
| `--paper` | `#FAF8F3` | page background, card foot, topbar bg (90% alpha) |
| `--paper-2` | `#F2EFE7` | hover background |
| `--surface` | `#FFFFFF` | card body, scrubber, secondary button |
| `--ink-1` | `#14130F` | primary text, company name |
| `--ink-2` | `#3D3C36` | role title, meta body |
| `--ink-3` | `#6B6A62` | tertiary text, "Haven't applied", subtitle |
| `--ink-4` | `#9C9B91` | meta icons, disabled |
| `--line-1` | `#E8E5DC` | hairline border, divider |
| `--line-2` | `#D6D3C8` | hover border, button border |
| `--accent` | `#1F6B47` | moss — wordmark dot, italic page-header em, applied state, remote pill |
| `--accent-hover` | `#1A5C3C` | accent button hover |
| `--accent-soft` | `#E6EFE9` | remote pill bg, applied-toggle hover bg |
| `--tier-s` | `#1F6B47` | Top picks accent stripe + bar + icon + swatch (same as accent moss) |
| `--tier-b` | `#B8732E` | Next best accent stripe + bar + icon + swatch (amber) |

### Typography

- **Sans + display:** `Geist` (weights 400, 500, 600, 700; italics on display). Loaded from Google Fonts. Local fallback in `fonts/` of the design system project.
- **Mono:** `Geist Mono` (weights 400, 500). Used for numerics (salary, count, dates) and eyebrow/meta labels.
- **Stack:** `var(--font-sans)` → `"Geist", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif`.

**Size / weight reference (used in this view):**

| Element | Family | Size | Weight | Style | Tracking | Line-height |
|---|---|---|---|---|---|---|
| `apt.` wordmark | Geist | 26px | 700 | italic | -0.04em | 1.0 |
| Page heading `h1` | Geist | 42px | 600 | italic em / upright body | -0.03em | 1.05 |
| Page subtitle | Geist Mono | 11px | 400 | upper | 0.08em | 1.3 |
| Section title | Geist | 17px | 600 | — | -0.005em | 1.25 |
| Section count | Geist Mono | 11px | 400 | upper | 0.08em | — |
| Company name | Geist | 22px | 600 | — | -0.02em | 1.1 |
| Role title | Geist | 14px | 500 | — | 0 | 1.35 |
| Meta items | Geist | 12px | 400 | — | — | — |
| Meta numerics ($, posted) | Geist Mono | 12px | 400 | — | — | — |
| Remote pill | Geist Mono | 11px | 500 | — | — | — |
| Buttons | Geist | 12.5px | 500 | — | — | 1.4 |
| Scrubber label | Geist | 13px | 500 | — | — | — |
| Scrubber day stamp | Geist Mono | 11px | 400 | — | — | — |
| Toggle label | Geist | 12.5px | 400/500 | — | — | — |

### Spacing (4px scale)

`--s-1` 4 · `--s-2` 8 · `--s-3` 12 · `--s-4` 16 · `--s-5` 20 · `--s-6` 24 · `--s-7` 32 · `--s-8` 40 · `--s-9` 56 · `--s-10` 72 · `--s-11` 96 · `--s-12` 128.

Notable gaps:
- Cards within a section: 12px (`--s-3`).
- Page-header → summary: 22px.
- Section → section: 28px.
- Card body padding: `18px 22px 14px`.
- Card foot padding: `10px 22px`.

### Radii

- 4px (chips) · 6px (buttons, scrubber chevrons) · 10px (cards — `--r-3`) · 14px (large surfaces) · 999px (pills, scrubber container, toggle hit area).

### Shadows

- Cards: **none**. Hairline border only. This is a deliberate house rule.
- Modals/popovers (not used here): `var(--shadow-3)`, `var(--shadow-4)`.
- Focus: `var(--shadow-focus)` = `0 0 0 3px rgba(31, 107, 71, 0.22)`. Apply on `:focus-visible` for all interactive elements.

### Motion

- `--ease-out`: `cubic-bezier(0.2, 0.7, 0.2, 1)`.
- Durations: 120ms (hovers, toggles), 180ms (base), 260ms (modal/panel mount).
- **No bounces, no scale-from-0, no parallax.**

---

## Iconography

Uses **Lucide** glyphs at 1.5px stroke, 24px artboard. In production, install `lucide-react` and use:

```jsx
import { MapPin, Clock, ExternalLink, Star, TrendingUp, ChevronLeft, ChevronRight, Calendar, Circle, CheckCircle2 } from 'lucide-react';
```

The prototype inlines a subset in `icons.jsx` for offline use; you can delete that file in production.

Glyphs used:

| Concept | Lucide name | Size in this view |
|---|---|---|
| Top picks badge | `star` | 16px |
| Next best badge | `trending-up` | 16px |
| Location | `map-pin` | 13px |
| Posted age | `clock` | 13px |
| Date in scrubber | `calendar` | 14px |
| Scrubber prev/next | `chevron-left` / `chevron-right` | 15px |
| Applied (off) | `circle` | 16px |
| Applied (on) | `check-circle-2` | 16px |
| Open posting | `external-link` | 13px |

**No emoji** in product UI.

---

## Copy reference

Exact strings used (sentence case throughout; no exclamation points; mono for numerics).

| Surface | String |
|---|---|
| Page heading | `{N} openings worth a look today.` |
| Page subtitle | `WED · MAR 12 · UPDATED 14 MIN AGO` (driven by server) |
| Legend (top) | `{N} top picks` |
| Legend (next) | `{N} next best` |
| Total | `{N} openings` |
| Section A | `Top picks` |
| Section B | `Next best` |
| Section count | `{N} opening(s)` |
| Status, off | `Haven't applied` |
| Status, on | `Applied` |
| Action | `Open posting` |
| Scrubber labels | `Today` · `Yesterday` · `{N} days ago` |

---

## Assets

- `design-system/assets/favicon.svg` — the favicon (moss dot inside a thin circle).
- The wordmark `apt.` is inline SVG + text, not an external asset.
- **Company logos are intentionally absent.** See "Open questions".

---

## Open questions / decisions to flag with design + PM

1. **Company logos.** The earlier iteration had a colored avatar tile with 2-letter initials. We removed it because there's no systematic source for real logos. Long-term decision: do we (a) integrate a logo CDN (Clearbit, Logo.dev) and re-add the tile, (b) generate consistent typographic initials, or (c) keep logos out and lean on the company name as the visual anchor? Currently it's (c).
2. **Bucket cut.** The prototype hardcodes `topPicks` / `nextBest`. In production, the boundary comes from tier; confirm with PM which tiers fall into each bucket.
3. **Empty state.** Not designed yet. Voice guide: `Nothing new today. Check back tomorrow, or loosen your filters.`
4. **Filters.** Not in this view; Apt's full design system has a filter bar pattern. Bring this back when filters are scoped.
5. **Snooze / archive.** Removed when we stripped the sidebar. If the app needs these, we'll need to re-add per-card actions or a card overflow menu.

---

## Files in this bundle

| Path | Purpose |
|---|---|
| `Ranked Openings.html` | Entry HTML. Loads React/Babel CDN scripts, then the four JSX files. |
| `styles.css` | All view-level CSS. Imports the design-system token sheet at the top. |
| `app.jsx` | Main React app — `App`, `TopBar`, `PageHeader`, `SummaryRow`, `Section`, `JobCard`. |
| `data.jsx` | Sample data — `RANKED.topPicks`, `RANKED.nextBest`. Replace with API calls. |
| `icons.jsx` | Inline Lucide-style icons. Delete in production; use `lucide-react`. |
| `tweaks-panel.jsx` | Design-time Tweaks panel (accent stripe variant, density, italic accent toggle). **Not production** — remove before ship. |
| `design-system/colors_and_type.css` | The token layer. Port to your codebase. |
| `design-system/assets/favicon.svg` | Favicon. |

## Running the prototype locally

Open `Ranked Openings.html` in any browser. No build step. Babel transpiles JSX at runtime via CDN (fine for design review; not for production).

To turn it into a production app:

1. Spin up a Vite + React (or Next.js) project.
2. Port `design-system/colors_and_type.css` as a global stylesheet.
3. Translate `app.jsx` into idiomatic components (`<JobCard>`, `<SectionHeader>`, `<DateScrubber>`).
4. Replace `data.jsx` with API calls; back the "applied" state with your database (one row per user × opening).
5. Replace the inline icon JSX with `lucide-react` imports.
6. Delete `tweaks-panel.jsx` and any `accent-*` / `density-*` / `greet-hidden` root classes.
