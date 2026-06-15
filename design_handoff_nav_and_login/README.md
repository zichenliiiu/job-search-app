# Handoff: Navigation refactor + pre-login marketing page

## Overview

This handoff covers two connected changes to the Apt web app:

1. **Introduce real routing.** Today the app is a single component gated by a `view` state (`'feed' | 'settings'`) with no router. Replace this with `react-router-dom` so every screen has a real URL: a public marketing/login page at `/`, and a guarded app at `/app/*`. This fixes broken browser back/forward, makes screens linkable and refresh-safe, and gives Settings a proper home instead of a one-way `view` toggle.
2. **Add a pre-login marketing page** at `/` — logo, a one-line blurb, and a "Log in with Google" button — replacing the bare `LoginPage` card.

The navigation model is **top bar + account menu** (no left sidebar). The feed is the whole product and owns the canvas; Settings and Log out live in an avatar account menu in the top bar. Opening Settings navigates to its own route and the top bar switches context (date scrubber → "Back to feed"), so it reads as going somewhere rather than a panel.

**Scope:** Only surfaces that exist today — pre-login, feed, feed-by-date, settings. Routes for future surfaces (job detail, saved, tracker, onboarding) are named in the route map as reserved but are **explicitly out of scope** — do not build them.

## About the design files

The files in this bundle (`Navigation — Feed & Settings.dc.html`, `Sitemap & Flow.dc.html`) are **design references authored in HTML** — prototypes showing intended look and behavior, not production code to copy. They use inline styles for prototyping. **Your task is to recreate these designs in the existing React codebase using its established patterns** — the existing CSS classes in `src/styles/app.css` and tokens in `src/styles/tokens.css`. Do **not** port the inline styles; map each piece to the existing class system and add new classes only where noted below.

> Note: these are `.dc.html` design-component files and won't render standalone in a plain browser (they depend on a runtime). Use the screenshots (if included) and the detailed specs in this README as the source of truth. The README is self-sufficient.

## Fidelity

**High-fidelity.** Final colors, typography, spacing, and copy. Recreate pixel-faithfully using the codebase's existing classes and tokens. All visual values below already exist as CSS custom properties in `src/styles/tokens.css` — reference those tokens, don't hardcode hex.

---

## Tech setup

- Stack: React 19, Vite 6, `lucide-react`. No router currently installed.
- **Add dependency:** `react-router-dom` (v6 or v7).
- Backend (Flask, see `api.py`) already provides: `GET /api/auth/me`, `GET /api/auth/login/google`, `POST /api/auth/logout`, `GET /api/dates`, `GET /api/feed?date=`, `GET|PUT /api/criteria`, `GET|PUT /api/companies`.

---

## Route map

**In scope (build these):**

```
/                      Pre-login marketing page (public)
/app                   → redirect to /app/feed
/app/feed              Today's digest (most recent date)
/app/feed/:date        A specific day's digest (date = the `date` value from /api/dates)
/app/settings          Settings (ranking criteria + followed companies)
*                      → redirect to /app/feed (if authed) or / (if not)
```

**Reserved — DO NOT build (named only so the structure has room later):**
`/app/job/:id`, `/app/saved`, `/app/tracker`, `/app/onboarding`.

### Guards & redirects

Implement a `RequireAuth` wrapper around `/app/*`:

- **No session** hitting `/app/*` → redirect to `/` (carry intended path as `?return_to=<path>` so they can be returned after login). *Backend note: the Google OAuth callback currently always redirects to `/`; to honor `return_to`, it should redirect to the `return_to` value when present, else `/app/feed`. If backend changes are out of scope for this pass, at minimum land authed users on `/app/feed` — see next point.*
- **Has session** hitting `/` → redirect to `/app/feed`.
- Auth state still loading → render nothing / a minimal loader (matches today's `if (authLoading) return null`).

### Date in the URL

Move the date scrubber position out of `dateIdx` state and into the URL:

- `/app/feed` = the most recent date (index 0 of `/api/dates`, which returns newest-first today).
- `/app/feed/:date` = the matching entry from `/api/dates`.
- Prev/next buttons `navigate()` to the adjacent date's `/app/feed/:date`. This makes a given day shareable, refresh-safe, and back-button navigable.

---

## Screens

### 1. Pre-login marketing page  (`/`, public)

Replaces `src/components/LoginPage.jsx`.

- **Purpose:** Explain the product in one line and get the user to Google login.
- **Layout:** Full viewport, background `--paper-2` (or `--paper`). Single centered column, vertically and horizontally centered, `max-width: ~600px`, `text-align: center`, generous padding (~72px 32px).
- **Components (top to bottom):**
  1. **Logo lockup** — horizontal, centered, gap ~13px, margin-bottom ~44px:
     - Ring mark SVG (reuse the one already in `LoginPage.jsx` / `TopBar.jsx`): `viewBox 0 0 64 64`, outer `<circle r=28 stroke=#14130F stroke-width=3 fill=none>`, inner `<circle r=9 fill=#1F6B47>`. Render ~38×38.
     - Wordmark "apt." — `font-family: var(--font-display)`, `font-style: italic`, `font-weight: 700`, `font-size: ~42px`, `letter-spacing: -0.04em`, color `--ink-1`, with the `.` in `--accent`.
  2. **Headline** — exact copy: **Worthy companies, right roles.**
     - `font-family: var(--font-display)`, `font-weight: 600`, `font-size: ~52px`, `line-height: 1.04`, `letter-spacing: -0.03em`, color `--ink-1`, margin-bottom ~18px.
     - The phrase **"right roles."** is wrapped in an accent span: `font-style: italic; color: var(--accent)`. (The headline wraps naturally at the comma into two lines.)
  3. **Blurb** — exact copy: **Pick the companies worth your time and describe a great role in your own words. Apt brings back only the openings that clear both.**
     - `font-size: 17px`, `line-height: 1.55`, color `--ink-2`, `max-width: ~460px`, centered, margin-bottom ~36px.
  4. **"Log in with Google" button** — white pill-less button:
     - `background: var(--surface)`, `border: 1px solid var(--line-2)`, `border-radius: var(--r-2)` (6px), padding ~13px 22px, `font-size: 15px`, `font-weight: 500`, color `--ink-1`, `box-shadow: var(--shadow-2)`, inline-flex, gap 11px.
     - Leading icon: the **4-color Google "G"** (SVG provided in the Assets section). 18×18.
     - **This is an `<a href="/api/auth/login/google">`** (same target as today's login button). If `return_to` is present in the URL, append it: `/api/auth/login/google?return_to=<encoded>`.
     - Exact label: **Log in with Google**
  5. **Trust line** — exact copy: **We only use Google to sign you in — nothing is posted on your behalf.** `font-size: 12.5px`, color `--ink-3`, margin-top ~16px.

> New CSS: add a `.prelogin` (or similar) block. You can reuse `--paper-2` background like the current `.login-page`. The current `.login-btn` is moss-filled; the new Google button is white/bordered — add a distinct class (e.g. `.btn-google`).

### 2. Feed  (`/app/feed`, `/app/feed/:date`)

This is today's feed, essentially unchanged in content. **The job cards must stay exactly as they are today** (`src/components/JobCard.jsx` + `.jcard` styles) — company name as headline, role, location row with optional remote pill, "Open posting" button, 2px top accent bar (moss for top picks, amber for next best). Do **not** add logos, scores, tier pills, tags, salary, or recruiter lines.

- **Layout:** `.topbar` (sticky) + `.content` column (existing). Inside: `PageHeader`, `SummaryRow`, then the two `Section`s (Top picks / Next best) with `JobCard`s. All of this already exists — keep it.
- **Top bar (feed context)** — modify `src/components/TopBar.jsx`:
  - Left: brand lockup (`.tb-brand`) — **make it a real home link** to `/app/feed` (currently `href="#"`). Use `<Link>`.
  - Right (`.tb-right`): the **date scrubber** (`.scrubber`, unchanged markup) + the **avatar account button** (new — replaces the inline `Settings` and `Sign out` buttons).
  - **Remove** the two inline `btn-ghost` "Settings" / "Sign out" buttons from the top bar; those actions move into the account menu (below).

### 3. Account menu  (avatar dropdown in the top bar)

New component, e.g. `src/components/AccountMenu.jsx`.

- **Trigger:** a 32×32 circular avatar button, `border-radius: var(--r-pill)`, `background: var(--accent)`, white initials (derive from `user.name`/`user.email`), `font-family: var(--font-mono)`, `font-size: 11px`, `font-weight: 600`. On open, add a 3px moss focus halo (`--shadow-focus`).
- **Dropdown:** absolutely positioned below the avatar, right-aligned, `width: ~248px`, `background: var(--surface)`, `border: 1px solid var(--line-1)`, `border-radius: var(--r-4)` (or 12px), `box-shadow: var(--shadow-4)`, overflow hidden. Open/close on click; close on outside-click and Esc.
  - **Header row:** avatar (34px) + name (`--ink-1`, 13px, weight 600) + email (`--ink-3`, 11px, truncated). Bottom hairline border `--line-1`.
  - **Item — Settings:** lucide `Settings` icon (16px, `--ink-2`) + label "Settings". Navigates to `/app/settings`. Row padding ~9px 10px, `border-radius: var(--r-2)`, hover `background: var(--paper-2)`.
  - **Divider:** 1px `--line-1`.
  - **Item — Log out:** lucide `LogOut` icon (16px, `--ink-3`) + label "Log out". Calls the existing logout handler (`POST /api/auth/logout`), then navigate to `/` (not a bare card).
- **Copy:** menu items are sentence case: "Settings", "Log out". (Today's top bar says "Sign out" — switch to "Log out" to match the design, or keep consistent app-wide; pick one and use it everywhere.)

### 4. Settings  (`/app/settings`)

Today's `src/components/SettingsPage.jsx`, rehomed as a route. Keep all functionality: ranking criteria (top + next-best descriptions), followed companies (chips with `pending` state, add by name), Save changes. **Do not redesign the form fields** — only the chrome around it changes.

- **Top bar (settings context)** — the top bar switches to signal "a place you went":
  - Left: a **"Back to feed"** control — lucide `ArrowLeft` (17px, `--accent`) + label "Back to feed", as a ghost button that navigates to `/app/feed`. (Today this back button lives *inside* `SettingsPage`'s `.page-head`; move it into the top bar. Either keep the brand lockup too or replace it with the back control — the design replaces the scrubber area with Back-to-feed + a "Settings" label.)
  - A hairline divider, then a mono uppercase "Settings" label (`--font-mono`, 11px, `letter-spacing: 0.08em`, `--ink-3`).
  - Right: the same avatar account menu.
  - **Remove the date scrubber** in this context — it's not relevant on Settings.
- **Content:** existing `.settings-page` content. The in-page `.page-head` "Back to feed" button is now redundant (moved to top bar) — remove it; keep the `<h1>Settings</h1>` (or move the page title styling to match — the design shows an italic display "Settings" heading using the same treatment as `.page-head h1`).
- **Save model:** keep today's explicit "Save changes" button + "Saved" confirmation. (The mock also shows a "Cancel" affordance — optional; today's code has no cancel, so leave it out unless desired.)

---

## Interactions & behavior

- **Brand lockup** → navigates home (`/app/feed` when authed).
- **Avatar** → toggles account menu; outside-click / Esc closes it; focus-visible shows moss halo.
- **Settings item** → `navigate('/app/settings')`.
- **Back to feed** (top bar, settings context) → `navigate('/app/feed')`. Browser back also works now (real route).
- **Log out** → `POST /api/auth/logout` → `navigate('/')`.
- **Date prev/next** → `navigate` to adjacent `/app/feed/:date`; disabled at ends (today's `disabled` logic).
- **Log in with Google** → `<a href="/api/auth/login/google[?return_to=…]">` (full-page nav, not SPA).
- **Transitions:** keep them quiet, per design system — fades/translates only, `--ease-out`, durations 120/180ms. No scale/bounce. The menu can fade+translate in over `--dur-base`.

## State management

- **Remove** `view` state from `App.jsx`; screen is determined by the route.
- **Remove** `dateIdx` state; derive the current date from the route param (`:date`) and the `/api/dates` list. Keep `dates`, `feed`, `user`, `authLoading`, `loading` fetching as today.
- Lift `user` + `onLogout` to wherever the routed layout can read them (a layout route that renders `<TopBar>` + `<Outlet/>`), or via context.
- Feed fetch keys off the route date instead of `dates[dateIdx]`.
- Account-menu open/closed is local component state.

## Design tokens

**Do not redefine tokens** — they already exist in `src/styles/tokens.css`. Key ones used here:
`--paper`, `--paper-2`, `--surface`, `--ink-1`, `--ink-2`, `--ink-3`, `--line-1`, `--line-2`, `--accent` (#1F6B47), `--accent-hover`, `--tier-s` (moss, top picks bar), `--tier-b` (amber, next best bar), `--font-display`, `--font-sans`, `--font-mono`, `--r-2` (6px), `--r-3` (10px), `--r-4` (14px), `--r-pill`, `--shadow-2`, `--shadow-4`, `--shadow-focus`, `--ease-out`, `--dur-fast`, `--dur-base`.

## Assets

- **Logo mark / wordmark:** already inline in `LoginPage.jsx` and `TopBar.jsx` — reuse as-is.
- **Google "G" icon (new):** inline SVG, 18×18 —

```html
<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
  <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
  <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
  <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.997 8.997 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
  <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
</svg>
```

## Files

**Design references (in this bundle):**
- `Navigation — Feed & Settings.dc.html` — the four screens (00 Pre-login, 01 Feed, 02 Account menu, 03 Settings).
- `Sitemap & Flow.dc.html` — the full route map + auth-guard architecture (includes reserved/out-of-scope routes for context).

**Codebase files to edit (in `frontend/`):**
- `package.json` — add `react-router-dom`.
- `src/App.jsx` — replace `view` state with a router; add `RequireAuth`, layout route, redirects.
- `src/components/LoginPage.jsx` — replace with the pre-login marketing page (`/`).
- `src/components/TopBar.jsx` — home-link the brand; remove inline Settings/Sign-out; add the account menu; support feed vs. settings context.
- `src/components/AccountMenu.jsx` — **new** (avatar + dropdown).
- `src/components/SettingsPage.jsx` — rehome as `/app/settings` route; move Back-to-feed into the top bar.
- `src/styles/app.css` — add classes for the pre-login page, the Google button, and the account-menu dropdown. Reuse existing `.topbar`, `.jcard`, `.scrubber`, `.settings-*`, `.chip` classes.

**Out of scope:** job-card redesign (keep today's), and all reserved routes (job detail, saved, tracker, onboarding).
