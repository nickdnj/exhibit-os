# ExhibitOS Documentation

This folder is the full design record for ExhibitOS. It's written **design-first** — the
docs lead the code — so a newcomer (or a future maintainer) can understand not just *what*
ExhibitOS does but *why* every decision was made.

## Start here, by who you are

**You're with VCF / a museum (Doug, Jeff, curators, managers):**
1. [`VCF-PROPOSAL.md`](VCF-PROPOSAL.md) — the pitch: what ExhibitOS is and why it fits VCF.
2. [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) — what we need your input on. **This is where to collaborate.**
3. [`DIRECTUS.md`](DIRECTUS.md) — what Directus is (the free tool volunteers will author content in), in plain language.
4. [`PRD.md`](PRD.md) §1–3 — the vision, goals, and who it's for, in more depth.

**You want to build it (developers):**
1. [`PRD.md`](PRD.md) — product requirements: vision, personas, the four deliverable forms, scope.
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design: Directus as content system-of-record,
   ExhibitOS as renderers + fleet, the Display Profile model, content model, sync/cache, deployment.
3. [`UX-SPEC.md`](UX-SPEC.md) — wireframes and interaction specs for every screen and the dashboard.
4. [`DEV-PLAN.md`](DEV-PLAN.md) — epics, stories, and the v1 build order (mirrored as GitHub issues).

## The documents

| Doc | What it covers |
|---|---|
| [`PRD.md`](PRD.md) | Problem & vision, goals/non-goals, personas, content model, the four v1 deliverable forms, phased scope, resolved + open decisions. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Directus (content SoR) + ExhibitOS (renderers/sync/fleet); Display Profile & render path; Directus content model; two-tier cache; bridged fleet protocol; deployment topology; security; risks. |
| [`UX-SPEC.md`](UX-SPEC.md) | Authoring flow (in Directus), the three render targets (incl. landscape **and** portrait cards), the central dashboard, accessibility, and the design language. |
| [`DEV-PLAN.md`](DEV-PLAN.md) | Epics → stories with acceptance criteria, sequenced v1 build order, definition of done. |
| [`VCF-PROPOSAL.md`](VCF-PROPOSAL.md) | The museum-facing pitch — opportunity, solution, pilot, cost, and ask. |
| [`DIRECTUS.md`](DIRECTUS.md) | Plain-language primer on Directus — the free, self-hosted content tool ExhibitOS is built on, and why we chose it. |
| [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) | Decisions already locked + the questions still open for VCF collaboration. |

## Core idea, in one line

**Author an exhibit once → ExhibitOS publishes it everywhere** (interpretive card + QR,
video display, touchscreen interactive) and controls every screen from one dashboard.

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for how to get involved — no code required to help.
