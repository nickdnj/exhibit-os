# Development Plan: ExhibitOS v1

**Date:** 2026-05-31
**Status:** Active — issues created in `nickdnj/exhibit-os` milestone [v1 — Concurrent 3280 end-to-end](https://github.com/nickdnj/exhibit-os/milestone/1)
**Source docs:** `PRD.md` (v0.2) · `ARCHITECTURE.md` (v0.1) · `UX-SPEC.md` (v0.1)

---

## Definition of Done for v1

v1 is complete when ALL of the following are true:

1. Directus is running in Docker with the §4 content model, roles, and Flows.
2. All four render targets (card + print, video, touch interactive, dashboard) read from the Tier-1 `content_cache`.
3. The Concurrent 3280 exhibit is authored end-to-end in Directus and rendering on 1–2 real InfoAge displays.
4. The printable 3280 card PDF has been reviewed against InfoAge's existing 9 signs and approved by InfoAge/VCF staff.
5. The Fleet tab shows the InfoAge device(s) as online; Reboot and Reload work without SSH.
6. **A non-technical InfoAge volunteer, given only the runbook, completes all 5 handoff workflows with zero developer involvement.** (PRD §8 — this is the headline test.)

v1 is **not** done if any display requires a developer touch for routine content or recovery tasks.

---

## Operational Handoff Principle

> We build things; we don't run things.

Every story in this plan should leave the system easier to hand off, not harder. The runbook and admin guide (Epic 9) are v1 deliverables, not afterthoughts. Validate with a real volunteer before calling v1 done.

---

## v1 Build Order

The sequence below is derived from the ARCHITECTURE.md §13 build order and maps to GitHub epics. Earlier epics unblock later ones. Epics 3 and 2 can progress in parallel after Epic 1 is underway.

```
Epic 1: Wharfside removal + rename     (foundation — unblocks everything)
    ↓
Epic 2: Table refactor                 (unblocks sync and renderers)
Epic 3: Directus setup                 (unblocks sync and content)
    ↓
Epic 4: Directus sync service          (unblocks renderers)
    ↓
Epic 5: Render targets                 (card, video, touch, Playwright print)
Epic 6: Fleet                          (exhibit-agent, Fully Kiosk, Fleet tab)
Epic 7: Admin dashboard                (overview, rooms, assets, settings)
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

### Epic 2 — SignBoard Table Refactor (DisplayAssignment, DisplayDevice, ContentCache)
**GitHub:** #2 · **Labels:** epic, refactor · **v1:** Yes

Replace `Page`/`Channel`/`ChannelPageAssignment` with three lean ExhibitOS models. `Page` held content body — that's gone (content lives in Directus). What remains is: a pointer to a Directus asset (DisplayAssignment), physical device state (DisplayDevice), and a read cache (ContentCache).

| # | Story | Size | Notes |
|---|-------|------|-------|
| #14 | Replace Page/Channel/ChannelPageAssignment with DisplayAssignment, DisplayDevice, ContentCache | M | Core model surgery; new indexes on `content_cache` |
| #15 | Build `GET /api/display/<room-slug>` with form-precedence logic | M | Gate: `device_class` → assignment form → `default_form`; error states for no-assignment, class-mismatch |
| #16 | Build `/api/assignments` admin CRUD | S | Backs the Rooms screen assignment panel; triggers `notify_content_changed` on save |

---

### Epic 3 — Directus Setup (Docker Compose, Content Model, Roles, Flows)
**GitHub:** #3 · **Labels:** epic, directus, infra · **v1:** Yes

Stand up Directus in the 3-service Docker Compose stack. Define all five collections with exact fields and relations (including the self-referential `related_assets` M2M). Configure four roles and two Flows: the media-attribution enforcement Flow and the publish webhook that triggers ExhibitOS sync.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #17 | Add Directus + Postgres services to docker-compose.yml (3-service stack) | S | `.env.example` included; ExhibitOS memory 2G |
| #18 | Create Directus content model: asset, room, person, media_item, setting | M | Schema snapshot to repo for reproducibility; repeater interface on `bullet_facts` |
| #19 | Configure Directus roles, permissions, and publish validation Flow | M | 4 roles; Flow blocks uncredited media from publishing; webhook Flow fires on publish |

---

### Epic 4 — Directus Sync Service (Webhook, Poll Loop, Media Mirror, Cache)
**GitHub:** #4 · **Labels:** epic, directus · **v1:** Yes

The sync layer that makes Directus outages transparent to displays. Webhook-triggered (near-real-time) + 5-minute poll (safety net). Mirrors content into SQLite `content_cache` and media files into `/data/media`. Renderers read only from this cache — never from Directus live.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #20 | Build `directus_client.py` wrapper and `/api/sync/webhook` + `/api/sync/status` endpoints | M | HMAC validation on webhook; fire-and-forget background task |
| #21 | Build `directus_sync.py` orchestrator: poll loop, full resync, media mirror | M | Delta-based poll; ETag-checked media download; prune orphans on resync |

---

### Epic 5 — Render Targets (Card + Print, Video, Touch Interactive)
**GitHub:** #5 · **Labels:** epic, renderer · **v1:** Yes

All four v1 render targets. One shared `InfoAgeHouseCard` component drives both the on-screen card and the Playwright PDF export — the same Chromium renders both, so they cannot drift. The touch interactive enforces the `device_class` gate: a passive device assigned the interactive form falls back to card.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #22 | Build `InfoAgeHouseCard.tsx` and `RoomDisplay.tsx` with Service Worker (Tier-2 cache) | L | 8-element layout per UX-SPEC §4.2; WebSocket re-render; `vite-plugin-pwa` |
| #23 | Build Playwright print service (`print_service.py`) and `/api/print/card` endpoint | M | Dockerfile gains Chromium layer; print CSS on `/_print/` route; **confirm sign size with InfoAge before implementing** (UX-SPEC §10 item 1) |
| #24 | Build `VideoDisplay.tsx` renderer | M | Looped muted autoplay; room-feed mode; operating hours; no demo video |
| #25 | Build `TouchInteractive.tsx` with gallery, person bio, and related-exhibit navigation | L | 3-level navigation; 90s idle; 2-hop cross-exhibit cap; `prefers-reduced-motion` |

---

### Epic 6 — Fleet (exhibit-agent, Fully Kiosk Bridge, Fleet Tab)
**GitHub:** #6 · **Labels:** epic, fleet · **v1:** Yes

Rename `signboard-agent` → `exhibit-agent`, wire the new `DEVICE_AGENT_TOKEN` WS handshake, and build the Fully Kiosk REST polling bridge. Two protocols, bridged not unified: Pi/legacy PC via WS push; Onn/Google TV via Fully Kiosk REST pull. Fleet tab in the dashboard surfaces both.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #26 | Rename signboard-agent → exhibit-agent, update WS device-agent protocol | M | New `/ws/device-agent` endpoint; bearer token; x86 path for legacy museum PCs |
| #27 | Implement Fully Kiosk REST bridge (`fully_kiosk.py`) and fleet API routes | M | 30s poll; off-channel detection; screenshot; rate-limited broadcast |

---

### Epic 7 — Admin Dashboard (Overview, Rooms, Assets, Settings)
**GitHub:** #7 · **Labels:** epic, dashboard · **v1:** Yes

Refactor the SignBoard admin into the ExhibitOS five-screen dashboard. The Rooms screen is the primary authoring-to-display handoff surface: curators assign published Directus content to physical displays here. The Fleet tab (in Epic 6) completes this epic.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #28 | Refactor admin shell: new sidebar, Overview screen, Directus sync banner | M | Replaces Wharfside nav; stale-sync banner polls every 60s |
| #29 | Build Rooms screen and Display detail panel (assignment, print export, fleet controls) | L | The PRD §8 headline test lives here: curator assigns without developer involvement |
| #30 | Build Assets screen and Fleet screen | L | Fleet screen includes register, broadcast modal, off-channel fix |

---

### Epic 8 — Concurrent 3280 Content + First Display Bring-Up at InfoAge
**GitHub:** #8 · **Labels:** epic, content · **v1:** Yes

The proof case. Author the 3280 end-to-end in Directus, render it on real InfoAge hardware, and get the printable card reviewed by InfoAge/VCF staff. This is not just a content task — it's the integration test that validates the whole platform.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #31 | Author Concurrent 3280 in Directus (media items, Ken Yeager, asset, SGI Onyx 10000 stub, relations) | M | UX-SPEC §3.6 happy path; all content published through the review workflow |
| #32 | First display bring-up at InfoAge: provision Pi, assign content, verify on real hardware | M | QR scan verification; Fleet tab shows device online; Reload/Reboot tested |
| #33 | Print proof: export 3280 card PDF, visual review against InfoAge's existing 9 signs | S | **Prerequisite: confirm sign dimensions with InfoAge before #23 (Playwright)** |

---

### Epic 9 — Operational Handoff (Runbook, Admin Guide, Volunteer Validation)
**GitHub:** #9 · **Labels:** epic, docs · **v1:** Yes · **Final gate**

The v1 final gate. A solution that requires Nick-in-the-loop forever is a failed solution (PRD §8). This epic delivers the runbook, the admin guide, and the observation of a real volunteer completing all 5 workflows.

| # | Story | Size | Notes |
|---|-------|------|-------|
| #34 | Write volunteer runbook (`docs/VOLUNTEER-RUNBOOK.md`) | M | 7 workflows; authoring-order dependency callout; printable |
| #35 | Write admin setup guide (`docs/ADMIN-SETUP.md`) + Directus license posture in README | M | Backup + recovery drill; token rotation; Directus license posture (ARCHITECTURE.md R1) |
| #36 | Validation test: non-technical InfoAge volunteer completes all 5 handoff workflows | M | Calendar-dependent — schedule early; document any friction; repeat until passes |

---

## Deferred to Later Phases

The following are explicitly out of v1 scope. They are documented here to prevent scope creep.

### Phase 2
- Full fleet expansion across the InfoAge gallery (many Pis + Onn sticks)
- Full SGI Onyx 10000 asset authored (content only — platform already supports it)
- SSO: Directus-as-IdP so volunteers have one login (removes the two-login v1 compromise, ARCHITECTURE.md D3/R6)
- Per-device log tail in Fleet tab; version-mismatch warnings; stale-device pruning
- Portrait-orientation card variant (UX-SPEC §10 item 6)
- Richer interactive content types (timelines, lineage diagrams)
- Offline-resilience hardening (configurable staleness window, Service Worker debug tooling)

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
| 3 | **Directus license verification** — confirm InfoAge/VCF qualifies for free self-hosted tier (<$5M revenue). Document posture in README for downstream museums. | #35 | ARCHITECTURE.md R1, PRD §9b #7 |
| 4 | **Directus review-workflow notification** — confirm Directus Flow to notify Reviewer when an asset enters "in_review" is in scope for v1, or simplify to manual email. | #19 | UX-SPEC §10 item 3 |
| 5 | **Mini PC RAM** — confirm target mini PC has 8GB+ (three services + Playwright want ~4GB allocated). | #17 | ARCHITECTURE.md §14 item 4 |
| 6 | **YouTube embed policy** — confirm InfoAge is fine embedding YouTube on the video display (already embedded on QR deep pages). Affects video renderer design. | #24 | ARCHITECTURE.md §14 item 5 |

---

## Estimation Summary

| Epic | Stories | Total Size | v1? |
|------|---------|-----------|-----|
| Epic 1: Wharfside removal + rename | 4 | 4×S = ~1 sprint | Yes |
| Epic 2: Table refactor | 3 | S+M+S = ~1 sprint | Yes |
| Epic 3: Directus setup | 3 | S+M+M = ~1.5 sprints | Yes |
| Epic 4: Sync service | 2 | M+M = ~1 sprint | Yes |
| Epic 5: Render targets | 4 | L+M+M+L = ~3 sprints | Yes |
| Epic 6: Fleet | 2 | M+M = ~1 sprint | Yes |
| Epic 7: Dashboard | 3 | M+L+L = ~2 sprints | Yes |
| Epic 8: Content + bring-up | 3 | M+M+S = ~1.5 sprints | Yes |
| Epic 9: Handoff | 3 | M+M+M = ~1.5 sprints + calendar | Yes |
| **Total** | **27 stories** | **~14 sprint-weeks at 1 dev** | — |

_Sizes: S = < 1 day, M = 1–3 days, L = 3–5 days. Estimates include testing. Adjust based on actual team velocity._

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-05-31 | Dev Planning (AI-assisted) | Initial plan. 9 epics, 27 stories, v1 build order, deferred phase list, open items flagged to Nick. GitHub issues created in `nickdnj/exhibit-os` milestone 1. |
