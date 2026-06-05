# Development Plan: ExhibitOS v1

> **Content architecture:** the docent wiki is the source of truth — see
> [`decisions/0001-content-source.md`](decisions/0001-content-source.md) (a CMS was explored and
> passed on).

**Date:** 2026-06-05
**Status:** Active — issues in `nickdnj/exhibit-os` milestone [v1 — Concurrent 3280 end-to-end](https://github.com/nickdnj/exhibit-os/milestone/1)
**Source docs:** `PRD.md` (v0.4) · `ARCHITECTURE.md` (v0.3) · `UX-SPEC.md` (v0.3)

---

## Definition of Done for v1

v1 is complete when ALL of the following are true:

1. ExhibitOS ingests the docent wiki into the `Exhibit` read-cache (idempotent upsert by slug; ExhibitOS-owned display fields preserved). **(The file-ingest slice is built.)**
2. All four render targets (card + print, video, touch interactive, dashboard) read from the `Exhibit` read-cache.
3. The Concurrent 3280 exhibit is authored in the wiki, ingested, and rendering on 1–2 real InfoAge displays.
4. The printable 3280 card PDF has been reviewed against InfoAge's existing 9 signs and approved by InfoAge/VCF staff.
5. The Fleet tab shows the InfoAge device(s) as online; Reboot and Reload work without SSH.
6. **A non-technical InfoAge volunteer, given only the runbook, completes the handoff workflows (author in the wiki → Re-ingest → set display assets → assign → recover a screen) with zero developer involvement.** (PRD §8 — this is the headline test.)

v1 is **not** done if any display requires a developer touch for routine content or recovery tasks.

---

## Operational Handoff Principle

> We build things; we don't run things.

Every story in this plan should leave the system easier to hand off, not harder. The runbook and admin guide (Epic 9) are v1 deliverables, not afterthoughts. Validate with a real volunteer before calling v1 done.

---

## v1 Build Order

The sequence below is derived from the ARCHITECTURE.md §13 build order and maps to GitHub epics. Earlier epics unblock later ones. The wiki-ingest content path (Epic 3) has a **built slice** already.

```
Epic 1: Wharfside removal + rename     (foundation — unblocks everything)
    ↓
Epic 2: Table refactor                 (DisplayAssignment / DisplayDevice — unblocks renderers)
Epic 3: Wiki ingest                    (Exhibit read-cache — file ingest BUILT; live API + polish remain)
    ↓
Epic 5: Render targets                 (card, video, touch, Playwright print)
Epic 6: Fleet                          (exhibit-agent, Fully Kiosk, Fleet tab)
Epic 7: Admin dashboard                (overview, rooms, exhibits + Re-ingest, settings)
    ↓
Epic 8: 3280 content + display bring-up
    ↓
Epic 9: Operational handoff            (v1 final gate)
```

---

## Epics and Stories

### Epic 1 — Wharfside Module Removal and SignBoard → ExhibitOS Rename
**GitHub:** #1 · **Labels:** epic, refactor · **v1:** Yes

Strip all Wharfside-specific code (Tempest weather, NOAA tides, surf, fishing, lightning, TagSmart) and rename every SignBoard identifier to ExhibitOS. This produces the clean MIT fork that ExhibitOS is meant to be. No museum content should exist in the codebase; no Wharfside branding should survive.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #10 | Remove Wharfside server modules (weather, tides, surf, fishing, lightning) | S | Delete 13+ Python files + seed calls in `main.py` |
| #11 | Remove Wharfside client components (WeatherPage, TidePage, SurfPage, FishingPage, LightningPage) | S | Delete 8 React components + admin managers |
| #12 | Rename SignBoard → ExhibitOS: docker-compose, config, main, logger, WS manager | S | Key rename: `notify_page_update` → `notify_content_changed(room_slug)` |
| #13 | Replace SignBoard design tokens with ExhibitOS museum-neutral theme | S | UX-SPEC §9.2 token set; remove Wharfside navy/gold |

---

### Epic 2 — SignBoard Table Refactor (DisplayAssignment, DisplayDevice)
**GitHub:** #2 · **Labels:** epic, refactor · **v1:** Yes

Replace `Page`/`Channel`/`ChannelPageAssignment` with lean ExhibitOS models. `Page` held content body — that's gone (narrative comes from the wiki via the `Exhibit` read-cache, already built in Epic 3). What remains here is: a pointer to an `Exhibit` (DisplayAssignment) and physical device state (DisplayDevice).

| # | Story | Size | Notes |
|---|-------|------|-------|
| #14 | Replace Page/Channel/ChannelPageAssignment with DisplayAssignment, DisplayDevice | M | Core model surgery; `display_assignment` points at an `Exhibit` by slug |
| #15 | Build `GET /api/display/<room-slug>` with form-precedence logic | M | Gate: `device_class` → assignment form → `default_form`; reads the `Exhibit` read-cache; error states for no-assignment, class-mismatch |
| #16 | Build `/api/assignments` admin CRUD | S | Backs the Rooms screen assignment panel; triggers `notify_content_changed` on save |

---

### Epic 3 — Wiki Ingest (Exhibit read-cache, DokuWiki parser, Re-ingest)
**GitHub:** #3 · **Labels:** epic, ingest · **v1:** Yes

Ingest the docent wiki into the `Exhibit` read-cache. The **file-ingest slice is built**; the remaining work is the live DokuWiki API and parser polish.

| # | Story | Size | Status / Notes |
|---|-------|------|-------|
| #17 | `Exhibit` model + `wiki_ingest.py` parser + idempotent upsert (content_hash; preserve ExhibitOS-owned fields) | M | **DONE** — `models/exhibit.py`, `services/wiki_ingest.py`; parses the `the_artifacts` dump (108 exhibits) |
| #18 | Exhibit API + CLI: public `GET /api/exhibits` (sort_order) + `GET /api/exhibits/{slug}`; authed `POST /api/exhibits/ingest`; `scripts.ingest_wiki` | S | **DONE** — `api/exhibits.py`, `scripts/ingest_wiki.py` |
| #19 | Live DokuWiki API ingest (XML-RPC/REST, read-only docent account) through the same parser, on a schedule | M | Remaining — replaces the manual export-file step; reuses `parse_dokuwiki()` |
| #19b | Parser polish: confirm exhibit-page detection + people/related-link extraction against the museum's real namespace | S | Remaining — depends on confirming the ingested wiki namespace (OPEN-QUESTIONS §4) |

---

### Epic 4 — QR Deep-Page + Public Deliverables
**GitHub:** #4 · **Labels:** epic, public · **v1:** Yes

The visitor-facing deep page the QR points to. The docents' wiki is login-gated, so a **public** deep page is needed (ExhibitOS-hosted public `/exhibit/:slug` page, or a VCF public wiki section — OPEN-QUESTIONS §2).

| # | Story | Size | Notes |
|---|-------|------|-------|
| #20 | Public interpretive card route `/exhibit/:slug` + auto-rotating collection "show" at `/show` | M | **Partially built** — public card + `/show` exist; finalize QR target + deep-page content |
| #21 | QR resolution (`{qr_base_url}/{slug}` with per-exhibit `deep_content_url` override) + scan verification | S | Confirm public deep-page host with VCF before wiring the QR target |

---

### Epic 5 — Render Targets (Card + Print, Video, Touch Interactive)
**GitHub:** #5 · **Labels:** epic, renderer · **v1:** Yes

All four v1 render targets. One shared `InfoAgeHouseCard` component drives both the on-screen card and the Playwright PDF export — the same Chromium renders both, so they cannot drift. The touch interactive enforces the `device_class` gate: a passive device assigned the interactive form falls back to card.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #22 | Build `InfoAgeHouseCard.tsx` and `RoomDisplay.tsx` with Service Worker (Tier-2 cache) | L | 8-element layout per UX-SPEC §4.2; WebSocket re-render; `vite-plugin-pwa` |
| #23 | Build Playwright print service (`print_service.py`) and `/api/print/card` endpoint | M | Dockerfile gains Chromium layer; print CSS on `/_print/` route; **confirm sign size with InfoAge before implementing** (UX-SPEC §10 item 1) |
| #24 | Build `VideoDisplay.tsx` renderer | M | Looped muted autoplay; room-feed mode; operating hours; no demo video |
| #25 | Build `TouchInteractive.tsx` with gallery, people, and related-exhibit navigation | L | 3-level navigation; 90s idle; 2-hop cross-exhibit cap; reads the `Exhibit` read-cache; `prefers-reduced-motion` |

---

### Epic 6 — Fleet (exhibit-agent, Fully Kiosk Bridge, Fleet Tab)
**GitHub:** #6 · **Labels:** epic, fleet · **v1:** Yes

Rename `signboard-agent` → `exhibit-agent`, wire the new `DEVICE_AGENT_TOKEN` WS handshake, and build the Fully Kiosk REST polling bridge. Two protocols, bridged not unified: Pi/legacy PC via WS push; Onn/Google TV via Fully Kiosk REST pull. Fleet tab in the dashboard surfaces both.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #26 | Rename signboard-agent → exhibit-agent, update WS device-agent protocol | M | New `/ws/device-agent` endpoint; bearer token; x86 path for legacy museum PCs |
| #27 | Implement Fully Kiosk REST bridge (`fully_kiosk.py`) and fleet API routes | M | 30s poll; off-channel detection; screenshot; rate-limited broadcast |

---

### Epic 7 — Admin Dashboard (Overview, Rooms, Exhibits, Settings)
**GitHub:** #7 · **Labels:** epic, dashboard · **v1:** Yes

Refactor the SignBoard admin into the ExhibitOS five-screen dashboard. The Rooms screen is the primary content-to-display handoff surface: curators assign ingested exhibits to physical displays here. The Exhibits screen lists the read-cache with a **Re-ingest** action and lets curators set the ExhibitOS-owned display fields. The Fleet tab (in Epic 6) completes this epic.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #28 | Refactor admin shell: new sidebar, Overview screen, last-ingest banner | M | Replaces Wharfside nav; banner shows last ingest time + counts |
| #29 | Build Rooms screen and Display detail panel (assignment, print export, fleet controls) | L | The PRD §8 headline test lives here: curator assigns without developer involvement |
| #30 | Build Exhibits screen (read-cache list, Re-ingest, set display assets, "View in wiki") and Fleet screen | L | Exhibits screen wraps the built `POST /api/exhibits/ingest`; Fleet screen includes register, broadcast modal, off-channel fix |

---

### Epic 8 — Concurrent 3280 Content + First Display Bring-Up at InfoAge
**GitHub:** #8 · **Labels:** epic, content · **v1:** Yes

The proof case. Author the 3280 in the docent wiki, ingest it, render it on real InfoAge hardware, and get the printable card reviewed by InfoAge/VCF staff. This is not just a content task — it's the integration test that validates the whole platform.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #31 | Author Concurrent 3280 in the wiki (Ken Yeager, SGI Onyx 10000 link), ingest it, set display assets (hero/video) | M | UX-SPEC §3.4 happy path; narrative authored + revised in the wiki |
| #32 | First display bring-up at InfoAge: provision Pi, assign content, verify on real hardware | M | QR scan verification; Fleet tab shows device online; Reload/Reboot tested |
| #33 | Print proof: export 3280 card PDF, visual review against InfoAge's existing 9 signs | S | **Prerequisite: confirm sign dimensions with InfoAge before #23 (Playwright)** |

---

### Epic 9 — Operational Handoff (Runbook, Admin Guide, Volunteer Validation)
**GitHub:** #9 · **Labels:** epic, docs · **v1:** Yes · **Final gate**

The v1 final gate. A solution that requires Nick-in-the-loop forever is a failed solution (PRD §8). This epic delivers the runbook, the admin guide, and the observation of a real volunteer completing the workflows.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #34 | Write volunteer runbook (`docs/VOLUNTEER-RUNBOOK.md`) | M | Author in the wiki → Re-ingest → set display assets → assign → print → recover a screen; printable |
| #35 | Write admin setup guide (`docs/ADMIN-SETUP.md`) + wiki-ingest setup posture in README | M | Backup + recovery drill; wiki-ingest source config (file path / live API access) |
| #36 | Validation test: non-technical InfoAge volunteer completes the handoff workflows | M | Calendar-dependent — schedule early; document any friction; repeat until passes |

---

## Deferred to Later Phases

The following are explicitly out of v1 scope. They are documented here to prevent scope creep.

### Phase 2
- **Live DokuWiki API ingest** on a schedule (Epic 3 #19), replacing the manual export-file step
- Full fleet expansion across the InfoAge gallery (many Pis + Onn sticks)
- Full SGI Onyx 10000 exhibit authored in the wiki (content only — platform already supports it)
- Per-device log tail in Fleet tab; version-mismatch warnings; stale-device pruning
- Richer interactive content types (timelines, lineage diagrams)
- Offline-resilience hardening (Service Worker debug tooling)

### Phase 3
- Multi-museum support (one deployment per museum is already the v1 model — Phase 3 adds turnkey packaging + documentation for external museums)
- New deliverable forms: audio-tour, projection mapping, mobile companion web app, large donor/wayfinding boards
- Open-source release packaging (GitHub Actions CI, Helm chart, install wizard)

---

## Open Items Flagged to Nick

These require a decision or confirmation before the affected stories can be fully implemented.

| # | Item | Blocks | Source |
|---|------|--------|--------|
| 1 | **Print canvas size** — confirm target physical sign dimensions with InfoAge/VCF before implementing #23 (Playwright). 1920×1080 at 150dpi ≈ 12.8"×7.2"; InfoAge signs appear to be ~24"×36". | #23, #33 | UX-SPEC §10 item 1 |
| 2 | **InfoAge house blue exact hex** — `#1A3A6B` is a working approximation. Match against a physical sign or InfoAge's design files before the print proof. | #33 | UX-SPEC §10 item 2 |
| 3 | **Wiki read access** — confirm the export method (v1) and that the DokuWiki API is enabled with a read-only docent account (live-API phase). | #19 | ARCHITECTURE.md §14 item 1, PRD §9b #7 |
| 4 | **Which wiki pages are exhibits** — confirm the namespace/page set ExhibitOS ingests and the exhibit-page convention (parser keys on level-5 headings today). | #19b | ARCHITECTURE.md §14 item 2, OPEN-QUESTIONS §4 |
| 5 | **Public deep-content host** — the wiki is gated; confirm whether ExhibitOS hosts the public `/exhibit/:slug` deep page or VCF opens a public wiki section. | #20, #21 | ARCHITECTURE.md §14 item 3, OPEN-QUESTIONS §2 |
| 6 | **Mini PC RAM** — confirm target mini PC has 8GB+ (single ExhibitOS service + Playwright want ~2GB; no CMS/Postgres). | #23 | ARCHITECTURE.md §14 item 4 |

---

## Estimation Summary

| Epic | Stories | Total Size | v1? |
|------|---------|-----------|-----|
| Epic 1: Wharfside removal + rename | 4 | 4×S = ~1 sprint | Yes |
| Epic 2: Table refactor | 3 | S+M+S = ~1 sprint | Yes |
| Epic 3: Wiki ingest | 4 | 2 DONE + M+S = ~1 sprint remaining | Yes |
| Epic 4: QR deep-page + public deliverables | 2 | M+S = ~1 sprint (partly built) | Yes |
| Epic 5: Render targets | 4 | L+M+M+L = ~3 sprints | Yes |
| Epic 6: Fleet | 2 | M+M = ~1 sprint | Yes |
| Epic 7: Dashboard | 3 | M+L+L = ~2 sprints | Yes |
| Epic 8: Content + bring-up | 3 | M+M+S = ~1.5 sprints | Yes |
| Epic 9: Handoff | 3 | M+M+M = ~1.5 sprints + calendar | Yes |
| **Total** | **28 stories** | **~13 sprint-weeks at 1 dev** (2 stories already done) | — |

_Sizes: S = < 1 day, M = 1–3 days, L = 3–5 days. Estimates include testing. Adjust based on actual team velocity._

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-05-31 | Dev Planning (AI-assisted) | Initial plan. 9 epics, 27 stories, v1 build order, deferred phase list, open items flagged to Nick. GitHub issues created in `nickdnj/exhibit-os` milestone 1. |
| 0.2 | 2026-06-05 | Dev Planning (AI-assisted) | **Content architecture refactor (ADR-0001).** Replaced the CMS-setup and sync-service epics with **Epic 3 — Wiki Ingest** (the file-ingest slice is BUILT: `Exhibit` model, `wiki_ingest.py`, `api/exhibits.py`, `scripts.ingest_wiki`; remaining = live DokuWiki API + parser polish) and **Epic 4 — QR deep-page + public deliverables**. Trimmed the table refactor to DisplayAssignment/DisplayDevice (the read-cache already replaces the content columns). Renamed the Assets screen to Exhibits + Re-ingest (Epic 7). Reframed Epic 8 (author in the wiki, ingest) and the handoff (Epic 9). Updated DoD, deferred list, open items, and estimates. Portrait card is v1 (removed from deferred). |
