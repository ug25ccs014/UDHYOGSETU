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
- [ ] **Step 2 – Auth + Dashboard shell**: `app/login/page.tsx`, `app/register/page.tsx`, `app/dashboard/layout.tsx`, `app/dashboard/page.tsx` (+ `features/NotificationBell.tsx`, `features/UnifiedCommandCenter.tsx` if used by dashboard home)
- [ ] **Step 3 – Project pages**: `app/dashboard/[projectId]/*` (approvals, documents, compliance, copilot, schemes, regulatory, simulate)
- [ ] **Step 4 – Applications/Explore/Officer pages** + `features/*` used by them
- [ ] **Step 5 – Remaining dashboard pages** (profile, inspections, sla-risk, grievances, notifications, integrations, demo) + final QA (alignment, mobile, build)

## Per-page "what am I doing?" pattern (use in Steps 2–5)
Each page starts with: title (`.page-title`) + one-line purpose (`.page-sub`) + a primary action button on the right, then content cards. Multi-step flows show a stepper with "Step X of Y".
