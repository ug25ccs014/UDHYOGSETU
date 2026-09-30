# UDYOGSETU UI Redesign — Progress Log

> Read this first when switching accounts. It says what is done, what is next, and which files to touch.
> Rule: only read the files listed under "Next", do not re-scan the whole project (saves credits).

## Design language (from NER Logistics, ner-logistics-nu.vercel.app)
- Cream base `#FFFFE3`, navy `#173A59`, accent blue `#3F7FD6`, teal `#2F9C84`, coral `#F07C61`, sun `#F2C94C`.
- Pill buttons, rounded-2xl cards, faint grid + aurora blobs, soft shadows (`shadow-card / soft / lift`).
- Motion: BlurText hero, ScrollReveal, Magnet CTA, SpotlightCard, Counter, CSS-3D IsoStack. All respect `prefers-reduced-motion`.
- **Tailwind `blue-*` and `gray-*` are remapped** in `tailwind.config.js` (blue → navy/blue, gray → warm ink/cream).
  So old classes like `bg-blue-600`, `text-gray-600`, `border-gray-200` already look on-theme. Prefer them; no need to rewrite each page's colours.
- Layout rule: page container = `mx-auto max-w-7xl px-5 sm:px-8`; grids use `gap-5`; headings use `.page-title` / `.page-sub`.

## Setup
```
cd frontend && npm install   # adds framer-motion
npm run dev
```
(Not build-tested inside the assistant sandbox — no network. Run `npm run build` once and report errors.)

## Steps
- [x] **Step 1 – Foundation + Landing** (DONE)
  - `tailwind.config.js`, `app/globals.css`, `app/layout.tsx` (Inter font), `package.json` (+framer-motion)
  - `components/fx/*` (ScrollReveal, BlurText, Magnet, SpotlightCard, AuroraBackground, Counter, IsoStack, usePrefersReducedMotion)
  - `components/ui/*` restyled (button, card, input, select, textarea, badge, loading) — same props/API
  - `app/page.tsx` landing rewritten (nav, hero + 3D stack, stats, scroll-progress "how it works", feature grid, CTA, footer)
- [x] **Step 1b – Landing polish after review** (DONE)
  - Hero: `components/fx/GlassStack.tsx` replaces IsoStack (**delete `components/fx/IsoStack.tsx`**). 5 tilted glass cards; hover/tap turns one to face you and shows a mini preview of that feature. Hit-testing is on the container so hover never flickers.
  - `components/landing/HowItWorks.tsx`: true zigzag (left/right alternating around a centre line), bigger cards with bullets, watermark numbers, scroll-filled line
  - (FeatureBento was added, then REMOVED by request — delete `components/landing/FeatureBento.tsx` if present)
  - `components/fx/ScrollReveal.tsx`: new optional `x` prop (slide from side)
  - `app/page.tsx`: now just composes hero + stats + `<HowItWorks/>` + `<FeatureBento/>` + CTA + footer
- [x] **Step 1c – Landing round 2** (DONE)
  - Nav: solid navy gradient bar with sun-yellow bottom border (like NER topbar); nav + hero share the same container/padding (`max-w-7xl px-5 sm:px-8 lg:px-14`) so logo, text and cards align
  - Hero: text indented further from the left edge, text + cards vertically centred on one axis; GlassStack cards bigger (460x250), auto-scale to column width, hint text removed
  - How it works: cards now compact rectangles (icon+title+desc, chip row); the opposite side of each row shows a "What you'll see" mini preview so no empty space
  - Features section removed from the landing page (and the nav link)
- [x] **Step 1d – Hero centring** (DONE): hero is `min-h-screen`, content vertically centred; text + nav shifted right (`lg:pl-20`), cards nudged right; GlassStack also scales to viewport height so all 5 cards + buttons are visible without scrolling; heading a bit smaller.
- [x] **Step 2 – Auth + Dashboard shell** (DONE)
  - NEW `components/AuthShell.tsx`: split layout (navy story panel + centred form), used by login/register
  - `app/login/page.tsx`: same logic, new UI, shows "Account created" notice after `?registered=1`, labels linked to inputs
  - `app/register/page.tsx`: same logic, "Step 1 of 2" label, phone + role on one row, password pair on one row
  - `app/dashboard/layout.tsx`: sidebar grouped (Start here / My work / Stay on track / More), navy active pill, top bar shows current page title, content capped at `max-w-7xl`, page fade-in on route change
  - `app/dashboard/page.tsx`: header + 3-step quick-start hero, project cards, spotlight capability grid; currency now ₹ (was $)
  - NotificationBell / UnifiedCommandCenter NOT edited (they inherit the remapped colours)
- [x] **Step 3-5 – Theme pass over ALL dashboard pages + feature panels** (DONE, scripted, 44 files in `app/` and `features/`)
  - every `<h1>` now uses `.page-title`; big stat numbers are extrabold
  - off-theme green/emerald classes remapped to the teal palette (semantic red/amber kept)
  - `rounded-lg` -> `rounded-xl`, `rounded-md` -> `rounded-lg` (softer NER-style corners)
  - colours/borders/cards/buttons/inputs already follow the theme through the remapped Tailwind `blue`/`gray` scale and restyled `components/ui/*`
  - translation calls (`useLanguage` / `t()`) were NOT touched
  - stale files removed: `components/fx/IsoStack.tsx`, `components/landing/FeatureBento.tsx`
- [x] **Step 6a – Hand polish, priority pages** (DONE)
  - NEW `components/PageHeader.tsx`: `PageHeader` (icon, title, purpose, optional "Step X of Y", action button), `StatCard`, `BackLink`. Use these on every page that is still polished by hand.
  - `app/dashboard/applications/page.tsx`: PageHeader + "New application" button, icon stat cards, filter chips with counts, statuses via `statusLabel()` (translated), pill action buttons
  - `app/dashboard/[projectId]/compliance/page.tsx`: PageHeader, redesigned metric cards, navy filter pills
  - `features/UnifiedCommandCenter.tsx` (project overview): navy hero banner with readiness meter, 8 KPI tiles as 2 rows of 4 with icon chips
  - `app/dashboard/[projectId]/page.tsx`: BackLink instead of ghost button
  - `tailwind.config.js`: `slate-*` and `violet-*` now follow the theme scales (older panels pick up the palette)
- [x] **Step 6b – Hand polish, second batch** (DONE)
  - `PageHeader` (+ `StatCard`) now on: Explore, Notifications (icon stat cards, navy "Unread only" toggle), Integrations (uppercase mini-labels on the 6 tiles), Officer Application Review
  - `features/OnboardingWizard.tsx`: "Step X of 5 · name" in the header, connected stepper (done = teal tick, current = navy with yellow ring), rounder card
  - `ApplicationPreparation` has no step structure in code, so it was left as is
- [x] **Step 6c – Hand polish, last batch** (DONE)
  - `PageHeader` now on: Business Profile (buttons moved into header), Inspection Planner, SLA & Risk, Grievances, Incentive Readiness (Schemes), Project Documents, Project Regulatory, Regulatory Updates, Project Copilot
  - `features/ScenarioSimulator.tsx`: navy hero banner (same style as project overview)
- [x] **Step 6d – Detail pages** (DONE)
  - `PageHeader` gained `badge` (status chip next to the title) and `capitalize` props
  - Now on: Application detail, Explore service detail, Officer application detail (+ `BackLink`), Demo Center
  - Left as is (already themed): application `prepare` and `query` pages (they render feature panels with their own headers)
- [x] **Step 8 – Hindi/Marathi for the new UI text** (DONE)
  - New `pg` section (98 keys) in `locales/en.ts`, `hi.ts`, `mr.ts` (compile-checked: a missing key in hi/mr fails the build)
  - `t('pg.…')` wired into: Dashboard home (incl. quick-start + 9 tool cards), Applications, Compliance, Notifications, Explore, Integrations, Officer list + detail back link/hint, project overview back link, New-project wizard (title, step label, step names), Business Profile, Inspection Planner, SLA & Risk, Grievances, Incentive Readiness, Documents, Regulatory, Copilot page headers
  - Still English (not covered): table column headings, empty/error states, card body text inside feature panels, Demo Center, application detail/prepare/query panels
- [ ] **Step 7 – Final QA (do on your machine)**: `npm ci && npm run build && npm test`; switch language to हिन्दी / मराठी and open each page; check alignment at ~1280px and ~375px. Send screenshots of anything off.
- [ ] **Deploy**: commit only the changed files, push; Render + Vercel redeploy automatically. No Neon / env changes.
