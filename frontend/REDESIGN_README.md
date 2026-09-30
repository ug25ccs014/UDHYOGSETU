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
- [x] **Step 2 – Auth + Dashboard shell** (DONE)
  - NEW `components/AuthShell.tsx`: split layout (navy story panel + centred form), used by login/register
  - `app/login/page.tsx`: same logic, new UI, shows "Account created" notice after `?registered=1`, labels linked to inputs
  - `app/register/page.tsx`: same logic, "Step 1 of 2" label, phone + role on one row, password pair on one row
  - `app/dashboard/layout.tsx`: sidebar grouped (Start here / My work / Stay on track / More), navy active pill, top bar shows current page title, content capped at `max-w-7xl`, page fade-in on route change
  - `app/dashboard/page.tsx`: header + 3-step quick-start hero, project cards, spotlight capability grid; currency now ₹ (was $)
  - NotificationBell / UnifiedCommandCenter NOT edited (they inherit the remapped colours)
- [ ] **Step 3 – Project pages**: `app/dashboard/[projectId]/*` (approvals, documents, compliance, copilot, schemes, regulatory, simulate)
- [ ] **Step 4 – Applications/Explore/Officer pages** + `features/*` used by them
- [ ] **Step 5 – Remaining dashboard pages** (profile, inspections, sla-risk, grievances, notifications, integrations, demo) + final QA (alignment, mobile, build)

## Per-page "what am I doing?" pattern (use in Steps 2–5)
Each page starts with: title (`.page-title`) + one-line purpose (`.page-sub`) + a primary action button on the right, then content cards. Multi-step flows show a stepper with "Step X of Y".
