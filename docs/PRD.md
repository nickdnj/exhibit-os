# Product Requirements Document: ExhibitOS

> **Content architecture:** the docent wiki is the source of truth — see
> [`decisions/0001-content-source.md`](decisions/0001-content-source.md) (a CMS was explored and
> passed on).

**Version:** 0.4
**Last Updated:** 2026-06-05
**Author:** Nick DeMarco, with AI assistance
**Status:** Draft
**Repo:** github.com/nickdnj/exhibit-os · local `~/Workspaces/exhibit-os`
**License:** MIT (free / open source throughout)

---

## 1. Problem & Vision

### 1.1 The problem

Museums tell stories about physical things — a machine, a room, a person — and today
that storytelling is fragmented across incompatible media:

- A **printed interpretive sign** next to the artifact (designed once in a layout tool, then frozen).
- A **video** playing on a nearby screen (a separate file on a separate device, separately managed).
- A **touchscreen** kiosk for visitors who want to go deeper (its own bespoke app).
- A **web/wiki page** the QR code points to (maintained somewhere else entirely).

Each form duplicates the same underlying facts — the title, the hero photo, the
credits, the backstory — and each is edited independently. When the curator corrects
a date or swaps a photo, they have to find and fix it in four places. Small museums run
by **volunteers** can't sustain that. The result: signs go stale, screens show the wrong
thing or nothing at all, and the rich cross-references between artifacts ("the architect
of *this* machine designed the chip inside *that* one, thirty feet away") never get told
because no single tool knows about both objects.

This is, at root, **a content-management problem wearing a hardware costume.**

### 1.2 The vision

**ExhibitOS is a free, open-source, distributed information-display platform for
museums. You model an exhibit's content once, and the system renders it many ways —
interpretive card, video display, touchscreen interactive — across every screen in the
building, all controlled from one dashboard.**

A volunteer author writes the story of an artifact a single time. ExhibitOS produces:
the on-screen card *and* a print-ready sign matching the museum's existing visual style;
the passive video display for the room; the tap-through interactive on the touchscreen by
the door; and the QR-linked deep-content page for the visitor's phone. Correct the date
once, and every surface updates.

The platform is **generic** — built for any museum. The **first deployment** is the
**Vintage Computer Federation (VCF) Museum @ InfoAge Science Center** in Wall Township,
NJ (the former Camp Evans / Fort Monmouth signal-corps site), where the first real
exhibit is the **Concurrent 3280** minicomputer. "More museums and more deliverable
forms to come" is an explicit design goal, not an afterthought.

### 1.3 Lineage and the core architectural bet

ExhibitOS is a clean-snapshot fork of **SignBoard**, a digital-signage system already
running at Wharfside Manor (pool / marina / laundry kiosks on Raspberry Pi and
streaming sticks, driven by a FastAPI + React + SQLite + WebSocket server). SignBoard is
good at one thing: **device-agnostic kiosk rendering and fleet control.** That is exactly
the part ExhibitOS keeps.

The bet that defines this PRD: **content management is already solved — by the museum's own
docent wiki — and we should not solve it again.** The VCF docents author placard text in their
existing **DokuWiki** today, which already gives them revision history, diffs, attribution, and
revert. Rather than grow SignBoard's SQLite schema into a homegrown CMS, *or* stand up a separate
CMS that would duplicate the wiki's version control, ExhibitOS **ingests** the wiki into a local
read-cache and renders it. The SignBoard core becomes a **thin ingest + renderer + fleet layer**.
A self-hosted CMS was explored and passed on; see
[`decisions/0001-content-source.md`](decisions/0001-content-source.md), which links to the
explored-option primer.

---

## 2. Goals & Non-Goals

### 2.1 Goals (v1)

1. **Author once, render many.** A single exhibit — authored in the docent wiki, ingested into
   one ExhibitOS `Exhibit` record — drives all four v1 deliverable forms. No content is
   duplicated per form.
2. **The docent wiki is the system of record.** All narrative content — title, interpretive
   text, key facts, people, relationships — and its revision history live in the **wiki**, where
   docents already author. ExhibitOS holds a **read-cache** of that content plus the things the
   wiki doesn't own: display assignment, schedules, the fleet, and deliverable assets (hero image,
   looping video, deep-content URL, location).
3. **Ship the Concurrent 3280 end-to-end.** One real exhibit, authored in the wiki and ingested,
   rendered as an on-screen card + printable sign + video display + touchscreen
   interactive, on one or two real displays at InfoAge, controlled from the dashboard.
4. **Match InfoAge's existing visual style.** Printable cards must visually belong
   alongside InfoAge's ~9 existing physical signs (ENIAC / UNIVAC / Wang house style).
5. **Transfer operational ownership.** A non-technical museum volunteer can author an
   exhibit (in the wiki they already use), then assign it to a display with **zero developer
   involvement.** This is a first-class product requirement (§8), not a nice-to-have.
6. **Free / open / cheap.** Docker on a mini PC; kiosks on Pi Zero 2 W (~$15) and Onn FHD
   streaming sticks (~$20); MIT licensed; content stays in the wiki the museum already runs.
7. **Tell cross-reference stories.** The model must make "related exhibit" first-class
   (the 3280 → SGI Onyx 10000 closed loop is the proof case).

### 2.2 Non-Goals (explicitly out of scope for v1)

- **Building (or running) a CMS.** ExhibitOS does not implement its own content editor,
  draft/approval workflow, or revision system, and does not run a separate CMS — the docent
  wiki provides authoring and version control. ExhibitOS's tables hold a read-cache of wiki
  content plus its own display-side fields, never the authoritative narrative.
- **Multi-museum tenancy / hosted SaaS.** v1 is a single-instance, single-museum
  install. Multi-museum support is a later phase (§7).
- **Ticketing, membership, POS, visitor analytics dashboards.** ExhibitOS displays
  content; it is not a museum-operations suite.
- **Native mobile/TV apps.** Displays are web clients rendered in a kiosk browser
  (Chromium on Pi; Fully Kiosk on streaming sticks/TVs). No App Store builds.
- **AI content generation.** Authors write content (possibly assisted elsewhere); the
  platform renders and distributes it.
- **Full MDM** (remote screen mirroring, per-device metric graphs, A/B OTA). Basic fleet
  control (reboot / reload / assign / status) only in v1; richer fleet ops later.

---

## 3. Personas & Key User Journeys

### 3.1 Persona A — Curator / Volunteer Author ("Doug")

A knowledgeable, non-technical museum volunteer. Comfortable with web forms and the docent
wiki he already uses; not comfortable with SSH, JSON, or "deploying." Wants to write the story
of an artifact and see it appear on the screens and in print. **This persona's success defines
the product** (see §8, "we build, we don't run").

**Journey — Author a new exhibit:**
1. Opens the **docent wiki** (the same DokuWiki he already writes placard text in) and edits
   the artifact's page: title, interpretive text, key facts, people, year. The wiki tracks the
   revision automatically.
2. In ExhibitOS, an admin (or a scheduled job) **re-ingests** the wiki so the new/edited page
   appears as an `Exhibit` in the read-cache. (v1: an admin clicks **Re-ingest** in the
   dashboard or runs the CLI; later: scheduled/live ingest.)
3. Doug opens the ExhibitOS dashboard and attaches the display-side fields the wiki doesn't
   hold — hero image, looping video, deep-content URL, location — and assigns the exhibit to
   the room's display, picking the deliverable form (card / video / interactive). Done — no
   developer touched it.

**Journey — Fix a typo:** Doug edits the artifact's page **in the wiki** and saves; the wiki
keeps the revision history. On the next ingest, every surface showing that exhibit updates.

**Journey — Print a sign:** Doug opens the exhibit in the dashboard, clicks **Export printable
card**, downloads a print-ready PDF matching InfoAge's house style, sends it to the museum's
sign printer.

### 3.2 Persona B — Visitor ("Maria")

A museum guest standing in front of an exhibit. Wants the story at three depths:
the **card** (30 seconds, the gist), the **video** (a few minutes, ambient), the
**touchscreen** (self-directed, as deep as she likes), and the **QR** (take it home /
go to the wiki + YouTube video on her own phone).

**Journey:** Reads the on-screen card → notices the QR → scans it → lands on the deep
wiki entry with embedded YouTube video → later walks to the touchscreen and taps through
the photo gallery and the "related exhibit" link to the Onyx 10000.

### 3.3 Persona C — System Admin ("Nick" / future volunteer admin)

Sets up the mini PC, configures the wiki-ingest connection, provisions kiosks, manages the
device fleet, and is the *only* persona allowed to touch infrastructure. The goal is to make
this persona **optional after install** — the curator persona handles day-to-day content (in
the wiki) and display assignment without escalating to admin.

**Journey — Provision a display:** Flash a Pi Zero 2 W (or set up an Onn stick with Fully
Kiosk), point it at the ExhibitOS display URL for its room, register it in the dashboard's
Fleet tab. It appears online; content assignment is now the curator's job.

**Journey — Recover a frozen screen:** Opens the Fleet tab, sees a device offline or
"off channel," clicks **Reload** (or **Reboot**), confirms it recovered — without leaving
the dashboard or SSHing anywhere.

---

## 4. System Architecture

### 4.1 The split and the contract

ExhibitOS has a clean boundary between **where content is authored** and **where it is
displayed**:

- **The docent wiki (DokuWiki) — the System of Record.** Owns ALL narrative content (title,
  interpretive text, key facts, people, year, relationships) and its revision history. The
  docents author and edit there, as they do today; the wiki provides accounts, diffs,
  attribution, and revert. ExhibitOS does **not** author narrative content.
- **ExhibitOS (the SignBoard core, refactored) — Ingest + Renderers + Fleet.** A FastAPI +
  React + SQLite + WebSocket app on the mini PC. It **ingests** the wiki (a DokuWiki export
  file today; the live DokuWiki API later) into a local **`Exhibit` read-cache**, renders
  content to devices by device class, exports printable cards, pushes content to the fleet,
  and manages overlays/schedules. It owns only the things the wiki doesn't: **display
  assignment, schedules, the fleet, and deliverable assets** (hero image, looping video,
  deep-content URL, location).

The contract: **the wiki is the only place narrative content is authored; ExhibitOS is the
only place displays are configured and controlled.** ExhibitOS's copy of the narrative is a
read-cache, refreshed by re-ingest; its display-side fields are its own.

### 4.2 Data-flow diagram (in text)

```
   ┌──────────────────────────────────────────────────────────────────┐
   │  AUTHORING (Docents — in the wiki they already use)                │
   │                                                                    │
   │   DokuWiki  ──authored by docents──▶  exhibit pages                │
   │   (accounts, page revisions,          title · interpretive text · │
   │    diffs, attribution, revert)        key facts · people · year   │
   │                                                                    │
   │                                                                    │
   │                                                                    │
   │                                                                    │
   └───────────────────────────────┬────────────────────────────────────┘
                  ingest: DokuWiki export file (today)  / live API (later)
                                    ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  EXHIBITOS SERVER (mini PC, Docker)  — INGEST · RENDER · FLEET      │
   │                                                                    │
   │   wiki_ingest ──▶ Exhibit read-cache (SQLite) + media on disk      │
   │      (idempotent upsert by slug via content_hash; preserves        │
   │       ExhibitOS-owned display fields; source order = display order)│
   │        │                                                           │
   │        ▼                                                           │
   │   Display-assignment config (SQLite — repurposed SignBoard tables):│
   │        which Device shows which Exhibit, in which Form, on what    │
   │        schedule, with what overlays (scheduled / emergency)        │
   │        │                                                           │
   │        ├─ Renderer: Interpretive Card + QR   (+ printable export)  │
   │        ├─ Renderer: Video Information Display                      │
   │        ├─ Renderer: Touchscreen Interactive  (touch class only)    │
   │        ├─ Public "show" (auto-rotating collection) at /show        │
   │        └─ Dashboard: assign content, schedule, overlay, FLEET ctl  │
   └───────────┬───────────────────────────────────┬────────────────────┘
       WebSocket push (Pi)              REST pull bridge (Fully Kiosk)
               ▼                                     ▼
   ┌────────────────────┐               ┌──────────────────────────────┐
   │ Pi Zero 2 W kiosk  │               │ Onn FHD stick / Google TV     │
   │ Chromium, agent     │               │ Fully Kiosk Browser, REST 2323│
   │ /display/<room>     │               │ /display/<room>               │
   └────────────────────┘               └──────────────────────────────┘
                                    │
                                    ▼
                          Visitor phone (QR) ──▶ deep content
                          (wiki entry + embedded YouTube video)
```

### 4.3 How SignBoard's existing tables are repurposed

The seeded repo carries SignBoard's schema (Page, Channel, SQLite store, WebSocket
fleet push, overlay/scheduling, kiosk rendering). The refactor:

| SignBoard concept (today) | Becomes in ExhibitOS | Notes |
|---|---|---|
| **Page** (held content body) | **Display assignment** — a pointer to an `Exhibit` (by slug/id) + chosen Form + render options | Content body fields are **emptied**; narrative now comes from the wiki via ingest. |
| **Channel** (a named feed a kiosk subscribes to) | **Room/Display feed** — the playlist of assigned exhibits for a device in a room | Keeps the subscribe-by-slug model (`/display/<room>`). |
| **SQLite content columns** | the **`Exhibit` read-cache** of ingested wiki content (§9) | Cache, not source of truth. The authoritative narrative is always the wiki. |
| **Overlay / schedule tables** | **Unchanged** — scheduled + emergency overlays | This is SignBoard's strength; carried forward as-is. |
| **`kiosks` table + agent protocol** | **Fleet table + device class** | Extended with `device_class` (passive / touchscreen) and `platform` (chromium-kiosk / fully-kiosk). |
| **JWT admin auth** | **Dashboard admin auth** | Reused for fleet + assignment control + the authed re-ingest trigger. |

### 4.4 The Exhibit read-cache and ingest (what is built)

There is no legacy museum content to migrate — exhibit narrative is authored in the wiki and
**ingested** into the `Exhibit` read-cache. The ingest path is built (see ARCHITECTURE.md §5):

- `server/services/wiki_ingest.py` parses a DokuWiki export, derives a url-safe `slug` per
  exhibit, and **idempotently upserts** by slug — refreshing the wiki-sourced fields only when
  the parsed `content_hash` changes, and **never overwriting** the ExhibitOS-owned display
  fields (`hero_image`, `video_url`, `deep_content_url`, `location`).
- Source order in the export drives `sort_order`, which drives display order.
- Re-ingest is triggered by the authed `POST /api/exhibits/ingest` (dashboard **Re-ingest**
  button), the `python -m scripts.ingest_wiki` CLI, or — later — a schedule / the live
  DokuWiki API through the same parser.

Any sample/demo content from the SignBoard SQLite store is **deleted, not migrated** — the
platform must never fall back to demo data (show error states instead; see §6/§9).

### 4.5 Reused SignBoard fleet patterns (cited)

ExhibitOS inherits SignBoard's two-protocol fleet model verbatim
(`signboard-fleet-management-spec.md`, `signboard-google-tv-spec.md`):

- **Pi Zero 2 W → WebSocket push.** A small persistent `exhibit-agent` (the SignBoard
  agent, renamed) connects to `WS /ws/device-agent`, sends a 10s heartbeat
  (`hostname, ip, version, uptime, mem_free, load_avg`), and handles `reboot`,
  `reload`, `update-scripts`. Server keeps an in-memory `dict[hostname → WebSocket]`.
- **Onn FHD stick / Google TV → Fully Kiosk REST pull.** No agent on-device; the
  dashboard polls each device's Fully Kiosk Remote Admin REST API (port 2323, LAN-only)
  for `deviceInfo`, and issues `loadURL`, `restartApp`, `rebootDevice`, `getScreenshot`,
  `screenOn/Off`.
- **The two protocols are bridged in the dashboard, not unified** — they have
  fundamentally different remote-access models, and forcing one abstraction adds
  complexity without value. (Direct quote of the SignBoard design decision.)
- Error handling carried forward: unreachable device → mark offline, keep last-known
  status, retry; URL drift → flag "off channel" with a one-click "Reload to correct URL."

---

## 5. Content Model — the `Exhibit` read-cache

Narrative content is authored in the docent wiki. ExhibitOS holds it in a single SQLite
read-cache model, `Exhibit`, populated by wiki ingest. There is **no CMS and no separate
collections** for rooms/people/media as content tables — those are either ExhibitOS-managed
display fields or future wiki-sourced fields, not a content database. (This model is built —
`server/models/exhibit.py`.)

### 5.1 The `Exhibit` model

One row per exhibit, keyed by a url-safe `slug` derived from the title. Fields split into
**wiki-sourced** (refreshed on re-ingest when `content_hash` changes) and **ExhibitOS-owned**
(set in the dashboard, **never** overwritten by re-ingest).

| Field | Type | Origin | Notes |
|---|---|---|---|
| `id` | int (PK) | system | autoincrement |
| `slug` | string (unique) | derived | url-safe id from the title, e.g. `concurrent-3280` |
| `title` | string | **wiki** | e.g. "The Concurrent 3280" |
| `year_introduced` | int (nullable) | **wiki** | parsed from the body/title where present |
| `sort_order` | int (indexed) | **wiki** | source position in the export → drives display order |
| `body_text` | text | **wiki** | interpretive narrative |
| `key_facts` | text | **wiki** | newline-joined bullet facts |
| `people` | string (nullable) | **wiki** | people associated with the exhibit (when present in the source) |
| `related_exhibits` | text (nullable) | **wiki/ExhibitOS** | cross-reference links (the 3280 ↔ Onyx 10000 case) — managed by ExhibitOS until the wiki carries them |
| `source_ref` | string | derived | provenance, e.g. `the_artifacts#<slug>` |
| `content_hash` | string | derived | hash of the parsed wiki content; idempotency key for re-ingest |
| `ingested_at` | datetime | derived | last ingest timestamp |
| `hero_image` | string (nullable) | **ExhibitOS** | deliverable asset — preserved across re-ingest |
| `video_url` | string (nullable) | **ExhibitOS** | self-hosted looping video — preserved across re-ingest |
| `deep_content_url` | string (nullable) | **ExhibitOS** | QR/phone deep-dive target — preserved across re-ingest |
| `location` | string (nullable) | **ExhibitOS** | physical location / room reference — preserved across re-ingest |

### 5.2 Rooms, people, related links, and media

- **Rooms / display feeds** are an ExhibitOS concept used for fleet routing (`/display/<room>`)
  and assignment — not a content collection. Authors think "this exhibit shows in the Main
  Gallery"; the dashboard maps rooms → devices.
- **People** arrive as a wiki-sourced field on `Exhibit` when the source provides them; richer
  structured person records are a future enhancement, not a v1 content table.
- **Related-exhibit links** are ExhibitOS-managed (the `related_exhibits` field), keyed to the
  exhibit slug, until/unless the wiki carries them as structured links.
- **Deliverable media** (hero image, looping video) are ExhibitOS-owned display fields, set in
  the dashboard and preserved across re-ingest. The wiki remains the source for narrative text;
  ExhibitOS owns the on-floor assets the wiki doesn't naturally hold.

### 5.3 Idempotent ingest (built)

`wiki_ingest.parse_dokuwiki()` + `ingest_from_file()` upsert by `slug`:

- **new slug** → insert a full row (wiki fields + empty ExhibitOS-owned fields).
- **existing slug, `content_hash` changed** → refresh the wiki-sourced fields only; the
  ExhibitOS-owned display fields are untouched.
- **existing slug, unchanged** → keep `sort_order` current and move on.

Counts (`created` / `updated` / `unchanged` / `total`) are returned to the caller so the
dashboard can report what a re-ingest did.

---

## 6. The Four v1 Deliverable Forms

Each form is **derived from one Asset record.** No form stores its own copy of content.

### 6.1 Form 1 — Interpretive Card + QR (on-screen **and** printable)

The card mirrors the structure of InfoAge's canonical sign template
(`~/Workspaces/wiki/projects/concurrent-3280-museum/museum-sign.md`), which is the house
style to match. Required structural elements, mapped to `Exhibit` fields (§5):

| Sign element (canonical template) | `Exhibit` field |
|---|---|
| Title (big blue sans-serif, top-left) | `title` (wiki) |
| Hero photo + caption (upper-left) | `hero_image` (ExhibitOS-owned) |
| Inventor / people credit (upper-right) | `people` (wiki, when present) |
| Bullets | `key_facts` (wiki) |
| "The Backstory:" sub-section | `body_text` (wiki) |
| QR code + caption (lower-right) | QR(`deep_content_url` else `{qr_base_url}/{slug}`) + fixed caption |
| Closer / easter-egg strip (bottom) | derived from `related_exhibits` / body |
| Year / dateline | `year_introduced` (wiki) |

**Requirements:**
- The on-screen renderer displays the card at the room's display URL for any `passive`
  device whose `default_form = card`.
- A **printable export** produces a print-ready file matching the `infoage-house`
  template proportions and typography (ENIAC/UNIVAC/Wang style), suitable for the
  museum's existing 9-sign portfolio.
- QR encodes the deep-content target, which resolves to the deep-content page (wiki entry +
  embedded YouTube video).
- The first real card is the **Concurrent 3280**, including the **SGI Onyx 10000**
  cross-reference (`related_exhibits`) rendered in the closer/backstory.

**Acceptance criteria:**
- [ ] Given an ingested exhibit, the on-screen card renders its structural elements from the
      `Exhibit` read-cache (no hardcoded content).
- [ ] The printable export of the 3280 card is visually consistent with InfoAge's
      existing signs when placed beside them (reviewed by InfoAge/VCF staff).
- [ ] The QR scans on a phone and lands on the correct deep-content page with a working
      embedded YouTube video.
- [ ] Editing the exhibit's wiki page and re-ingesting changes both the on-screen card and
      the next printable export, with no code change.
- [ ] The 3280's "related exhibit" (Onyx 10000) appears in the rendered closer/backstory.
- [ ] If the read-cache has no content for the room, the card shows a clear error
      state — **never demo/placeholder content** (see §9, §8).

### 6.2 Form 2 — Video Information Display

A passive screen playing self-hosted video for an exhibit or a whole room (generalized from
SignBoard's media-playback capability).

**Requirements:**
- Renders on any `passive` device with `default_form = video`.
- Plays the exhibit's self-hosted `video_url` (an ExhibitOS-owned deliverable asset served
  from the local mirror) in a loop; if a room is assigned (not a single exhibit), it cycles
  videos across the room's exhibits. **No YouTube iframe on kiosks** (escape risk); YouTube is
  the phone/QR deep-page only.
- Honors scheduled screen on/off from the room's operating hours.
- Muted autoplay by default (museum-appropriate); optional ambient audio per assignment.

**Acceptance criteria:**
- [ ] Assigning a video-bearing exhibit to a passive display plays its self-hosted video
      full-screen, looped, muted.
- [ ] A room assignment cycles through all the room's exhibits' videos in order.
- [ ] Screen powers off / on per operating hours (Pi via agent; Fully Kiosk via schedule).
- [ ] No demo video plays when content is missing — error state instead.

### 6.3 Form 3 — Touchscreen Interactive

Tap-through galleries and deeper dives, **gated to the `touchscreen` device class.**

**Requirements:**
- Renders only on devices with `device_class = touchscreen`. A `passive` device never
  serves the interactive form, even if mis-assigned (the renderer enforces the gate).
- Visitor can: scroll the interpretive body, read the key facts and people, view any
  gallery imagery, and tap a `related_exhibits` link to jump to the related exhibit's
  interactive view (the 3280 → Onyx 10000 traversal).
- Idle timeout returns to an attract/home screen.

**Acceptance criteria:**
- [ ] On a touchscreen device, the interactive renders the body, people, and
      related-exhibit navigation, all from the `Exhibit` read-cache.
- [ ] Tapping the Onyx 10000 cross-reference from the 3280 navigates to the Onyx
      interactive view and back.
- [ ] A passive device assigned the interactive form refuses it and shows an error/
      fallback to its `default_form` — the touch gate holds.
- [ ] After N seconds idle, the screen returns to the attract screen.

### 6.4 Form 4 — Central Multi-Display Dashboard (+ Fleet)

One admin surface controlling every sign across rooms / displays / assets, reusing
SignBoard's dashboard + fleet specs.

**Requirements — content control:**
- Browse ingested exhibits; assign an exhibit (or a Room feed) to a Display Device,
  choosing the deliverable Form and any render options.
- Set the ExhibitOS-owned display fields (hero image, video, deep-content URL, location)
  per exhibit, and trigger a **Re-ingest** from the wiki.
- Manage schedules and scheduled/emergency overlays (carried from SignBoard).
- Trigger a printable-card export for any exhibit.

**Requirements — fleet management (reuses `signboard-fleet-management-spec.md`):**
- **Fleet tab** lists every device with live status: hostname, room, IP, version, uptime,
  mem free, load, last seen, online/offline, `device_class`, `platform`.
- Per-device actions: **Reboot**, **Reload**, **Update**, plus **Screenshot / Screen
  on-off** for Fully Kiosk devices.
- **Broadcast** action to all online devices, with confirmation modals and rate limiting.
- Pi devices controlled via WebSocket agent; Onn/Google-TV via Fully Kiosk REST pull;
  bridged (not unified) in the UI.

**Acceptance criteria:**
- [ ] A curator can assign an ingested exhibit to a display in a chosen Form without
      developer involvement (this is also §8's headline criterion).
- [ ] The Fleet tab shows accurate online/offline within one heartbeat interval (Pi) or
      one poll interval (Fully Kiosk).
- [ ] Reboot / Reload work end-to-end on a real Pi and a real Onn stick.
- [ ] A scheduled overlay and an emergency overlay both appear on assigned displays.
- [ ] Assigning the touchscreen interactive to a passive device is prevented or warned in
      the UI (mirrors the renderer gate).

---

## 7. v1 Scope vs Later Phases

### 7.1 v1 — "3280 end-to-end" (the proof)

- The `Exhibit` read-cache model + the wiki-ingest path (export file → idempotent upsert).
  *(Built — `models/exhibit.py`, `services/wiki_ingest.py`, `scripts.ingest_wiki`.)*
- The four deliverable forms implemented as renderers reading the read-cache.
- Display-assignment refactor of SignBoard tables.
- **One real exhibit (Concurrent 3280)** authored in the wiki and ingested, including the
  Onyx 10000 cross-reference, hero photo, key facts, backstory, QR.
- Rendered on **one or two real displays** at InfoAge (e.g. one passive card display + one
  touchscreen), plus a passive video display if a second screen is available.
- Printable 3280 card matching InfoAge house style, reviewed by InfoAge/VCF staff.
- Dashboard with content assignment + Re-ingest + a working Fleet tab for the deployed devices.
- Operational handoff package (§8) delivered and validated with a real volunteer.

### 7.2 Phase 2 — Live wiki ingest + content depth

- **Live DokuWiki API ingest** (XML-RPC/REST) through the same parser, with scheduled re-ingest,
  replacing the manual export-file step.
- Full fleet across the gallery (many Pis + Onn sticks / Google TVs), broadcast ops,
  fleet polish (stale pruning, version-mismatch warnings, per-device log tail).
- More exhibits authored by docents in the wiki (the SGI Onyx 10000 as its own full record;
  additional VCF artifacts).
- Richer interactive content types (timelines, lineage diagrams).
- Offline-resilience hardening of the local cache (§9).

### 7.3 Phase 3 — More museums, more forms

- Multi-museum support (one deployment per museum is already the v1 model — Phase 3 adds
  turnkey packaging + documentation for external museums).
- New deliverable forms (audio-tour, projection mapping, mobile companion web app, large
  donor/wayfinding boards).
- Packaging ExhibitOS as a turnkey, documented open-source install for other small
  museums ("more museums and more deliverable forms to come").

---

## 8. Operational Handoff Requirements ("We Build, We Don't Run")

**Principle:** Nick (and any developer) builds ExhibitOS, then **transfers operational
ownership to non-technical museum volunteers before it ships.** A solution that requires
Nick-in-the-loop forever is a failed solution. This section is a **first-class product
requirement**, not documentation polish.

### 8.1 The handoff mechanism

- **The docent wiki** is the volunteer's content surface — the same tool they already use, with
  its own accounts, drafts, revision history, and revert. No JSON, no SSH, no code.
- **ExhibitOS dashboard** is the volunteer's display-control surface — set display assets,
  Re-ingest, assign content, schedule, export print, and recover a frozen screen via the
  Fleet tab.
- Together these mean **every routine task is self-service.**

### 8.2 Required handoff deliverables (part of v1 "done")

- A **volunteer runbook** (in-repo + printable) covering: author/edit an exhibit in the wiki,
  Re-ingest, set the display assets (hero/video/deep-link), assign to a display, export a
  printable card, and recover an offline/frozen screen.
- **Reliance on the wiki's own review/revision controls** — authors edit in the wiki, every
  change is a tracked, attributable, revertible revision. ExhibitOS implements no separate
  approval workflow.
- An **admin setup guide** for the one technical owner (mini PC, Docker, wiki-ingest
  connection, kiosk provisioning) — used once, then rarely.

### 8.3 Acceptance criteria (the headline test)

- [ ] **A non-technical museum volunteer, given only the runbook, can author a new exhibit in
      the wiki, Re-ingest it, and assign it to a display — start to finish, with zero
      developer involvement.** (Validated by observing a real InfoAge volunteer do it.)
- [ ] The same volunteer can recover a frozen display via the Fleet tab without SSH.
- [ ] No routine content or display task requires editing files, running scripts, or
      contacting a developer.
- [ ] When content is unavailable (a display offline, the read-cache empty for a room), the
      system shows a clear error state with a documented recovery step — **never
      demo/placeholder data.**

---

## 9. Open Questions / Decisions Needed

### 9a. Resolved Decisions

1. **Content source of truth → the docent wiki; ExhibitOS ingests. RESOLVED (2026-06-02).**
   The museum's existing DokuWiki is the system of record for exhibit narrative and its
   revision history; ExhibitOS ingests it into the `Exhibit` read-cache and renders it. No CMS
   and no separate edit/approval/revision system. A self-hosted CMS was explored and passed on.
   See [`decisions/0001-content-source.md`](decisions/0001-content-source.md).

2. **Display order → source order. RESOLVED.**
   Display order is driven by the exhibit's `sort_order` (its position in the wiki source),
   which the ingest sets and keeps current on every re-ingest. This is more reliable than the
   parsed `year_introduced` (many "years" in the source are model numbers, not dates).

3. **Re-ingest is idempotent. RESOLVED.**
   Ingest upserts by `slug`: wiki-sourced fields refresh only when the parsed `content_hash`
   changes; the ExhibitOS-owned display fields are never overwritten. Re-ingest is safe to run
   any number of times (admin Re-ingest button / CLI / future schedule).

4. **Printable-card export pipeline → Playwright (headless Chromium). RESOLVED.**
   The card renders on-screen *and* prints, and both must match each other and InfoAge's
   existing sign portfolio. Playwright drives the same Chromium that renders the on-screen
   card, so one HTML/CSS template yields pixel-identical screen and print output. The only
   cost — bundling Chromium in the image — is acceptable because export runs **server-side on
   the mini PC, never on kiosks**.

5. **QR resolution → configurable base URL + per-exhibit path. RESOLVED.**
   A single global `qr_base_url`; each exhibit has a `slug`; the QR resolves to
   `{qr_base_url}/{slug}`. Changing the base once repoints every QR. An exhibit's
   `deep_content_url` (ExhibitOS-owned) handles the case where one exhibit's deep content lives
   at a specific page (e.g. a vcfed.org wiki page).

6. **Multi-museum tenancy → one deployment per museum (Option A). RESOLVED.**
   Each museum runs its own ExhibitOS stack (and ingests its own wiki) on its own hardware;
   data is fully isolated per museum. "Generic platform" means *the same open-source code
   anyone can deploy*, not one shared instance. The schema stays single-museum.

### 9b. Still Open

7. **Wiki read access for ingest.** ExhibitOS needs a read path into the docent wiki. v1
   ingests a DokuWiki **export file**; the next step is the **live DokuWiki API** (XML-RPC/REST)
   with a read-only docent account, or a scheduled export. Confirm the wiki's API is enabled and
   agree on an access method (tracked in [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) §6).

8. **Public deep-content target for QR.** The docents' wiki is login-gated, so a *public*
   visitor-readable deep page is still needed (ExhibitOS hosts it, or VCF opens a public wiki
   section). Tracked in [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) §2.

9. **Form-per-exhibit vs. form-per-assignment overrides.** The chosen card template and the
   device's `default_form` both influence rendering. Decide the precedence rules when an
   assignment specifies a form different from the device default (e.g. can a curator force a
   card onto a video-default screen for a day?).

---

## 10. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-05-31 | Nick DeMarco (AI-assisted) | Initial first draft. Documented a self-hosted CMS as the content system of record, ExhibitOS as renderer+fleet, four v1 forms, 3280 first exhibit. (That content-source decision was later reversed — see 0.4 and ADR-0001.) |
| 0.2 | 2026-05-31 | Nick DeMarco (AI-assisted) | Resolved 4 open questions (§9a): Playwright card export; configurable `qr_base_url` + per-exhibit slug; two-tier cache (server mirror + kiosk-local); one-deployment-per-museum tenancy (schema stays single-museum). |
| 0.3 | 2026-06-01 | Nick DeMarco (AI-assisted) | Kept original link-target wiki architecture (no publish-to-wiki, no public-deep-page render target). **Kiosk video policy:** kiosks play self-hosted HTML5 `<video>` only — no YouTube iframe on kiosks (public-kiosk escape risk); YouTube reserved for phone/QR deep page. Added kiosk URL-allowlist navigation lockdown (issue #37). Media mirror now holds video binaries. |
| 0.4 | 2026-06-05 | Nick DeMarco (AI-assisted) | **Content architecture refactor (ADR-0001).** Rewrote the design around the **docent wiki as system of record + ExhibitOS wiki-ingest**: replaced the earlier two-systems/CMS framing (§1–§4) with wiki-ingest, and the multi-collection CMS content model (§5) with the single `Exhibit` read-cache model (slug/content_hash idempotency, ExhibitOS-owned display fields preserved across re-ingest, source-order ordering — all matching the built code). Updated the four forms (§6), v1 scope (§7), handoff (§8 — review via the wiki's own revision control), and resolved/open decisions (§9). The previously-evaluated CMS is kept only as the explored option (see ADR-0001, which links to the explored-option primer). |
