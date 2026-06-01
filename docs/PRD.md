# Product Requirements Document: ExhibitOS

**Version:** 0.1 (first draft)
**Last Updated:** 2026-05-31
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

The bet that defines this PRD: **content management is a solved problem, and we should
not solve it again.** Rather than grow SignBoard's SQLite schema into a homegrown CMS
(roles, revisions, approval workflows, a media library — all the things that take years
to get right), ExhibitOS adopts **Directus** as its content backbone and demotes the
SignBoard core to a **thin renderer + fleet layer** that consumes the Directus API.

---

## 2. Goals & Non-Goals

### 2.1 Goals (v1)

1. **Model once, render many.** A single Directus "Asset" record drives all four v1
   deliverable forms. No content is duplicated per form.
2. **Directus is the system of record.** All content — text, media, credits, relations,
   draft/published state, revision history — lives in Directus. ExhibitOS stores only
   *display-assignment config* (which device shows which asset, schedules, overlays).
3. **Ship the Concurrent 3280 end-to-end.** One real exhibit, authored in Directus,
   rendered as an on-screen card + printable sign + video display + touchscreen
   interactive, on one or two real displays at InfoAge, controlled from the dashboard.
4. **Match InfoAge's existing visual style.** Printable cards must visually belong
   alongside InfoAge's ~9 existing physical signs (ENIAC / UNIVAC / Wang house style).
5. **Transfer operational ownership.** A non-technical museum volunteer can add an
   exhibit, edit a card, and assign it to a display with **zero developer involvement.**
   This is a first-class product requirement (§8), not a nice-to-have.
6. **Free / open / cheap.** Docker on a mini PC; kiosks on Pi Zero 2 W (~$15) and Onn FHD
   streaming sticks (~$20); MIT licensed; Directus on its free self-hosted tier.
7. **Tell cross-reference stories.** The data model must make "related exhibit" a
   first-class relation (the 3280 → SGI Onyx 10000 closed loop is the proof case).

### 2.2 Non-Goals (explicitly out of scope for v1)

- **Re-implementing a CMS inside SignBoard.** Directus owns content. SignBoard's tables
  do not store interpretive copy, media, or credits after migration.
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

A knowledgeable, non-technical museum volunteer. Comfortable with web forms and Google
Docs; not comfortable with SSH, JSON, or "deploying." Wants to write the story of an
artifact and see it appear on the screens and in print. **This persona's success defines
the product** (see §8, "we build, we don't run").

**Journey — Author a new exhibit:**
1. Logs into Directus (museum-branded URL, his own login).
2. Creates a new **Asset** record: title, subtitle, hero photo (uploaded to the media
   library with caption + source + credit), interpretive body, bullet facts, a QR target.
3. Links the asset to a **Room**, to a **Person** (the inventor), to **MediaItems**, and
   optionally to a **related Asset** ("see also: SGI Onyx 10000").
4. Sets status to **Draft**, saves. A reviewer approves → status **Published**.
5. Opens the ExhibitOS dashboard, assigns the published asset to the room's display,
   picks the deliverable form (card / video / interactive). Done — no developer touched it.

**Journey — Fix a typo:** Doug opens the asset in Directus, edits one field, saves. Every
surface showing that asset updates on next refresh. Directus keeps the revision history.

**Journey — Print a sign:** Doug opens the asset, clicks **Export printable card** in the
dashboard, downloads a print-ready PDF matching InfoAge's house style, sends it to the
museum's sign printer.

### 3.2 Persona B — Visitor ("Maria")

A museum guest standing in front of an exhibit. Wants the story at three depths:
the **card** (30 seconds, the gist), the **video** (a few minutes, ambient), the
**touchscreen** (self-directed, as deep as she likes), and the **QR** (take it home /
go to the wiki + YouTube video on her own phone).

**Journey:** Reads the on-screen card → notices the QR → scans it → lands on the deep
wiki entry with embedded YouTube video → later walks to the touchscreen and taps through
the photo gallery and the "related exhibit" link to the Onyx 10000.

### 3.3 Persona C — System Admin ("Nick" / future volunteer admin)

Sets up the mini PC and Directus, provisions kiosks, manages the device fleet, and is
the *only* persona allowed to touch infrastructure. The goal is to make this persona
**optional after install** — the curator persona handles day-to-day content and
assignment without escalating to admin.

**Journey — Provision a display:** Flash a Pi Zero 2 W (or set up an Onn stick with Fully
Kiosk), point it at the ExhibitOS display URL for its room, register it in the dashboard's
Fleet tab. It appears online; content assignment is now the curator's job.

**Journey — Recover a frozen screen:** Opens the Fleet tab, sees a device offline or
"off channel," clicks **Reload** (or **Reboot**), confirms it recovered — without leaving
the dashboard or SSHing anywhere.

---

## 4. System Architecture

### 4.1 The two systems and their contract

ExhibitOS is **two cooperating systems** with a clean boundary:

- **Directus — the System of Record (SoR).** Owns ALL content and the authoring
  experience. Self-hosted Docker container, free tier (no feature paywall for orgs under
  $5M revenue). Provides roles, revision history, approval/review flows, a media library,
  and both REST and GraphQL APIs out of the box.
- **ExhibitOS (the SignBoard core, refactored) — Renderers + Fleet.** A FastAPI + React +
  SQLite + WebSocket app on the mini PC. It **consumes** the Directus API, renders content
  to devices by device class, exports printable cards, pushes content to the fleet, and
  manages overlays/schedules. It stores **no content** — only display-assignment config.

The contract: **Directus is the only place content is created or edited. ExhibitOS is the
only place displays are configured and controlled.** They never overlap.

### 4.2 Data-flow diagram (in text)

```
   ┌──────────────────────────────────────────────────────────────────┐
   │  AUTHORING (Curator / Volunteer)                                   │
   │                                                                    │
   │   Directus Admin UI  ──writes──▶  Directus (System of Record)      │
   │   (roles, drafts,                  ├─ Asset / Exhibit              │
   │    review/approve,                 ├─ Room / Location              │
   │    media library,                  ├─ Person                      │
   │    revision history)               ├─ MediaItem (caption/src/credit)│
   │                                    └─ relations (asset↔room↔person↔│
   │                                        media↔related-asset)        │
   └───────────────────────────────┬────────────────────────────────────┘
                                    │  REST / GraphQL  (read-only token)
                                    ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  EXHIBITOS SERVER (mini PC, Docker)  — RENDERERS + FLEET            │
   │                                                                    │
   │   Directus Sync ──▶ local cache (SQLite + media mirror)            │
   │        │                                                           │
   │        ▼                                                           │
   │   Display-assignment config (SQLite — repurposed SignBoard tables):│
   │        which Device shows which Asset, in which Form, on what      │
   │        schedule, with what overlays (scheduled / emergency)        │
   │        │                                                           │
   │        ├─ Renderer: Interpretive Card + QR   (+ printable export)  │
   │        ├─ Renderer: Video Information Display                      │
   │        ├─ Renderer: Touchscreen Interactive  (touch class only)    │
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
| **Page** (held content body) | **Display assignment** — a pointer to a Directus Asset ID + chosen Form + render options | Content body fields are **emptied**; content now lives in Directus. |
| **Channel** (a named feed a kiosk subscribes to) | **Room/Display feed** — the playlist of assigned assets for a device in a room | Keeps the subscribe-by-slug model (`/display/<room>`). |
| **SQLite content columns** | **Local read cache** of Directus content for offline resilience (§9) | Cache, not source of truth. Authoritative copy is always Directus. |
| **Overlay / schedule tables** | **Unchanged** — scheduled + emergency overlays | This is SignBoard's strength; carried forward as-is. |
| **`kiosks` table + agent protocol** | **Fleet table + device class** | Extended with `device_class` (passive / touchscreen) and `platform` (pi / fully-kiosk). |
| **JWT admin auth** | **Dashboard admin auth** | Reused for fleet + assignment control. |

### 4.4 Content migration (out of SignBoard tables, into Directus)

For v1 there is no legacy museum content to migrate (the 3280 is authored fresh in
Directus). The **engineering migration** is structural: a one-time refactor that
(a) creates the Directus collections (§5), (b) strips content fields from the
Page/Channel tables leaving only assignment pointers, and (c) adds the Directus Sync
service + local cache. Any sample/demo content currently in the SignBoard SQLite store is
**deleted, not migrated** — the platform must never fall back to demo data (show error
states instead; see §6/§9).

### 4.5 Reused SignBoard fleet patterns (cited)

ExhibitOS inherits SignBoard's two-protocol fleet model verbatim
(`signboard-fleet-management-spec.md`, `signboard-google-tv-spec.md`):

- **Pi Zero 2 W → WebSocket push.** A small persistent `exhibit-agent` (the SignBoard
  agent, renamed) connects to `WS /ws/kiosk-agent`, sends a 10s heartbeat
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

## 5. Directus Content Model

All collections live in Directus. Types below are Directus field types. Every collection
has implicit `id`, `status` (where noted), `date_created`, `date_updated`, `user_created`,
`user_updated` (Directus standard). Draft/Published gating uses the `status` field.

### 5.1 Collection: `asset` (Asset / Exhibit)

A physical display piece; the central record. Owns content reusable across all forms.

| Field | Type | Notes |
|---|---|---|
| `title` | string (required) | e.g. "The Concurrent 3280" |
| `subtitle` | string | e.g. "The last great pre-RISC scalar minicomputer" |
| `slug` | string (unique) | URL-safe id, e.g. `concurrent-3280` |
| `status` | string (draft / in_review / published / archived) | drives publish gating + approval flow |
| `hero_image` | M2O → `media_item` | primary photo for card/interactive |
| `interpretive_body` | text (rich/markdown) | the main narrative |
| `bullet_facts` | JSON (array of strings) | the bullet list (matches sign "Bullets") |
| `backstory` | text (rich/markdown) | the "Backstory" sub-section |
| `closer` | text | the closer / easter-egg strip line |
| `qr_target_url` | string (URL) | where the QR resolves (deep content) |
| `deep_content_url` | string (URL) | wiki entry / canonical deep page |
| `youtube_url` | string (URL) | YouTube for the phone/QR **deep-content page only** — NOT played on kiosks (on-floor video is self-hosted HTML5; 2026-06-01 policy) |
| `card_template` | string (enum: `infoage-house` / others) | which printable style to match |
| `featured` | boolean | for dashboard sorting |

**Relations:**
- `room` — M2O → `room` (where the asset physically lives)
- `people` — M2M → `person` (inventors / architects / curators)
- `media` — M2M → `media_item` (gallery, ordered via junction `sort`)
- `related_assets` — M2M self-referential → `asset` (cross-reference; the 3280 ↔ Onyx
  10000 case). Junction may carry a `relationship_note` string ("same architect, 30 ft away").

### 5.2 Collection: `room` (Room / Location)

A first-class place with display device(s), hours, and assigned content.

| Field | Type | Notes |
|---|---|---|
| `name` | string (required) | e.g. "VCF Main Gallery" |
| `slug` | string (unique) | feed id used by displays: `/display/<slug>` |
| `description` | text | optional room intro |
| `operating_hours` | JSON | per-day open/close, used for scheduled screen on/off |
| `floor_map_ref` | string | optional location reference |

**Relations:**
- `assets` — O2M ← `asset.room`
- `devices` — O2M ← `display_device.room`

### 5.3 Collection: `person` (Person)

Inventors / architects / curators (e.g. Ken Yeager).

| Field | Type | Notes |
|---|---|---|
| `name` | string (required) | "Ken Yeager" |
| `credentials` | string | "MIT '72" |
| `role_label` | string | "architect of the 3280" |
| `bio` | text (rich) | full bio for interactive/deep content |
| `portrait` | M2O → `media_item` | headshot |
| `lifespan` | string | optional ("1949–2017") |

**Relations:** `assets` — M2M ← `asset.people`.

### 5.4 Collection: `media_item` (MediaItem)

Photos/videos with **museum-grade attribution** (caption + source + credit are required
for published items).

| Field | Type | Notes |
|---|---|---|
| `file` | M2O → Directus `directus_files` | the actual upload (image or video) |
| `media_type` | string (enum: image / video / external_video) | external_video = YouTube/Vimeo URL |
| `external_url` | string (URL) | for external_video |
| `caption` | text (required for published) | shown under the image |
| `source` | string (required for published) | provenance ("Drive archive…", "techmonitor.ai") |
| `credit` | string (required for published) | attribution ("by then-co-op Nick DeMarco") |
| `alt_text` | string | accessibility |

**Relations:** used by `asset.hero_image`, `asset.media`, `person.portrait`.

### 5.5 Collection: `display_device` (Display Device)

A screen. **Note:** this collection is *mirrored* — devices are registered in the
ExhibitOS dashboard (the SoR for physical fleet state), and optionally represented in
Directus for authors to assign content to. Live fleet status (online, heartbeat, IP)
lives in the ExhibitOS SQLite fleet table, **not** Directus. See §9 open question on
where device registration canonically lives.

| Field | Type | Notes |
|---|---|---|
| `name` | string | "Main Gallery — left wall" |
| `device_class` | string (enum: `passive` / `touchscreen`) | **gates the interactive form** |
| `platform` | string (enum: `pi` / `fully-kiosk`) | selects fleet protocol |
| `default_form` | string (enum: `card` / `video` / `interactive`) | what it renders |
| `status` | string (active / maintenance / retired) | authoring-side state |

**Relations:** `room` — M2O → `room`.

### 5.6 Relations summary

```
asset ──M2O──▶ room
asset ──M2M──▶ person
asset ──M2M──▶ media_item        (hero_image is a distinct M2O)
asset ──M2M──▶ asset             (related_assets, self-referential, with note)
room  ──O2M──▶ display_device
person ─M2O──▶ media_item        (portrait)
```

---

## 6. The Four v1 Deliverable Forms

Each form is **derived from one Asset record.** No form stores its own copy of content.

### 6.1 Form 1 — Interpretive Card + QR (on-screen **and** printable)

The card mirrors the structure of InfoAge's canonical sign template
(`~/Workspaces/wiki/projects/concurrent-3280-museum/museum-sign.md`), which is the house
style to match. Required structural elements, mapped to Asset fields:

| Sign element (canonical template) | Asset field |
|---|---|
| Title (big blue sans-serif, top-left) | `title` |
| Hero photo + caption (upper-left) | `hero_image` → `media_item.file` + `.caption` |
| Inventor portrait + credit (upper-right) | `people[0].portrait` + `.name` + `.credentials` + `.role_label` |
| Bullets | `bullet_facts[]` |
| "The Backstory:" sub-section | `backstory` |
| QR code + caption (lower-right) | QR(`qr_target_url`) + fixed caption |
| Closer / easter-egg strip (bottom) | `closer` |
| Photo-slot list (production aid) | `media[]` with caption/source/credit |

**Requirements:**
- The on-screen renderer displays the card at the room's display URL for any `passive`
  device whose `default_form = card`.
- A **printable export** produces a print-ready file matching the `infoage-house`
  template proportions and typography (ENIAC/UNIVAC/Wang style), suitable for the
  museum's existing 9-sign portfolio.
- QR encodes `qr_target_url`, which resolves to the deep-content page (wiki entry +
  embedded YouTube video).
- The first real card is the **Concurrent 3280**, including the **SGI Onyx 10000**
  `related_assets` cross-reference rendered in the closer/backstory.

**Acceptance criteria:**
- [ ] Given a published Asset, the on-screen card renders all eight structural elements,
      pulling live from Directus (no hardcoded content).
- [ ] The printable export of the 3280 card is visually consistent with InfoAge's
      existing signs when placed beside them (reviewed by InfoAge/VCF staff).
- [ ] The QR scans on a phone and lands on the correct deep-content page with a working
      embedded YouTube video.
- [ ] Editing any source field in Directus changes both the on-screen card and the next
      printable export, with no code change.
- [ ] The 3280's "related exhibit" (Onyx 10000) appears in the rendered closer/backstory.
- [ ] If Directus is unreachable, the card shows the last-cached content or a clear error
      state — **never demo/placeholder content** (see §9, §8).

### 6.2 Form 2 — Video Information Display

A passive screen playing embedded video(s) for an asset or a whole room (generalized from
SignBoard's media-playback capability).

**Requirements:**
- Renders on any `passive` device with `default_form = video`.
- Plays the Asset's `youtube_url` (or `media_item`s of type video / external_video) in a
  loop; if a room is assigned (not a single asset), it cycles videos across the room's
  published assets.
- Honors scheduled screen on/off from the room's `operating_hours`.
- Muted autoplay by default (museum-appropriate); optional ambient audio per assignment.

**Acceptance criteria:**
- [ ] Assigning a video-bearing Asset to a passive display plays its video full-screen,
      looped, muted.
- [ ] A room assignment cycles through all published assets' videos in order.
- [ ] Screen powers off / on per operating hours (Pi via agent; Fully Kiosk via schedule).
- [ ] No demo video plays when content is missing — error state instead.

### 6.3 Form 3 — Touchscreen Interactive

Tap-through galleries and deeper dives, **gated to the `touchscreen` device class.**

**Requirements:**
- Renders only on devices with `device_class = touchscreen`. A `passive` device never
  serves the interactive form, even if mis-assigned (the renderer enforces the gate).
- Visitor can: scroll the interpretive body + backstory, swipe the `media[]` gallery
  (each with caption/source/credit), open `person` bios, and tap a `related_assets` link
  to jump to the related exhibit's interactive view (the 3280 → Onyx 10000 traversal).
- Idle timeout returns to an attract/home screen.

**Acceptance criteria:**
- [ ] On a touchscreen device, the interactive renders the gallery, person bios, and
      related-asset navigation, all from Directus.
- [ ] Tapping the Onyx 10000 cross-reference from the 3280 navigates to the Onyx
      interactive view and back.
- [ ] A passive device assigned the interactive form refuses it and shows an error/
      fallback to its `default_form` — the touch gate holds.
- [ ] After N seconds idle, the screen returns to the attract screen.

### 6.4 Form 4 — Central Multi-Display Dashboard (+ Fleet)

One admin surface controlling every sign across rooms / displays / assets, reusing
SignBoard's dashboard + fleet specs.

**Requirements — content control:**
- Browse published Directus Assets; assign an Asset (or a Room feed) to a Display Device,
  choosing the deliverable Form and any render options.
- Manage schedules and scheduled/emergency overlays (carried from SignBoard).
- Trigger a printable-card export for any Asset.

**Requirements — fleet management (reuses `signboard-fleet-management-spec.md`):**
- **Fleet tab** lists every device with live status: hostname, room, IP, version, uptime,
  mem free, load, last seen, online/offline, `device_class`, `platform`.
- Per-device actions: **Reboot**, **Reload**, **Update**, plus **Screenshot / Screen
  on-off** for Fully Kiosk devices.
- **Broadcast** action to all online devices, with confirmation modals and rate limiting.
- Pi devices controlled via WebSocket agent; Onn/Google-TV via Fully Kiosk REST pull;
  bridged (not unified) in the UI.

**Acceptance criteria:**
- [ ] A curator can assign a published Asset to a display in a chosen Form without
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

- Directus stood up in Docker with the §5 content model.
- The four deliverable forms implemented as renderers consuming Directus.
- Display-assignment refactor of SignBoard tables + Directus Sync + local cache.
- **One real exhibit (Concurrent 3280)** authored entirely in Directus, including the
  Onyx 10000 cross-reference, hero photo, Yeager portrait, bullets, backstory, QR.
- Rendered on **one or two real displays** at InfoAge (e.g. one passive card display + one
  touchscreen), plus a passive video display if a second screen is available.
- Printable 3280 card matching InfoAge house style, reviewed by InfoAge/VCF staff.
- Dashboard with content assignment + a working Fleet tab for the deployed devices.
- Operational handoff package (§8) delivered and validated with a real volunteer.

### 7.2 Phase 2 — Full fleet + content depth

- Full fleet across the gallery (many Pis + Onn sticks / Google TVs), broadcast ops,
  fleet polish (stale pruning, version-mismatch warnings, per-device log tail).
- More exhibits authored by volunteers (the SGI Onyx 10000 as its own full record;
  additional VCF artifacts).
- Richer interactive content types (timelines, lineage diagrams as first-class media).
- Offline-resilience hardening of the local cache (§9).

### 7.3 Phase 3 — More museums, more forms

- Multi-museum support (tenancy model TBD — see §9): multiple Directus instances vs. a
  single instance with a museum-scoping field.
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

- **Directus authoring UI** is the volunteer's content surface — no JSON, no SSH, no code.
  Roles restrict volunteers to authoring + the approval flow; admin/infra is separate.
- **ExhibitOS dashboard** is the volunteer's display-control surface — assign content,
  schedule, export print, and recover a frozen screen via the Fleet tab.
- Together these mean **every routine task is self-service.**

### 8.2 Required handoff deliverables (part of v1 "done")

- A **volunteer runbook** (in-repo + printable) covering: add an exhibit, edit a card,
  upload media with proper attribution, submit for review, assign to a display, export a
  printable card, and recover an offline/frozen screen.
- A **roles + review workflow** configured in Directus: Author → submits Draft →
  Reviewer approves → Published. No volunteer can break the live signs by accident.
- An **admin setup guide** for the one technical owner (mini PC, Docker, Directus, kiosk
  provisioning) — used once, then rarely.

### 8.3 Acceptance criteria (the headline test)

- [ ] **A non-technical museum volunteer, given only the runbook, can add a new exhibit,
      edit an existing card, and assign it to a display — start to finish, with zero
      developer involvement.** (Validated by observing a real InfoAge volunteer do it.)
- [ ] The same volunteer can recover a frozen display via the Fleet tab without SSH.
- [ ] No routine content or display task requires editing files, running scripts, or
      contacting a developer.
- [ ] When a backend service (Directus / a display) is unavailable, the system shows a
      clear error state with a documented recovery step — **never demo/placeholder data.**

---

## 9. Open Questions / Decisions Needed

### 9a. Resolved Decisions (2026-05-31)

1. **Printable-card export pipeline → Playwright (headless Chromium). RESOLVED.**
   The card renders on-screen *and* prints, and both must match each other and InfoAge's
   existing sign portfolio. Playwright drives the same Chromium that renders the on-screen
   card, so one HTML/CSS template yields pixel-identical screen and print output.
   WeasyPrint was rejected: its separate rendering engine drifts from the on-screen card
   and would force two maintained looks. The only cost — bundling Chromium in the image —
   is acceptable because export runs **server-side on the mini PC, never on kiosks**.

2. **QR resolution → configurable base URL + per-exhibit path. RESOLVED.**
   A single global setting `qr_base_url`; each Asset has a `slug`; the QR resolves to
   `{qr_base_url}/{slug}`. Changing the base once repoints every QR. An optional
   per-Asset **absolute-URL override** handles the exception case where one exhibit's deep
   content lives elsewhere (e.g. a specific vcfed.org wiki page). This supersedes the
   earlier open question on QR deep-content hosting — the *target* is configurable rather
   than hard-bound to any one host.

3. **Offline resilience → two-tier cache. RESOLVED.**
   (a) **Server-side mirror** on the mini PC: ExhibitOS holds the authoritative cached
   copy of Directus content + media; displays always hit ExhibitOS, never Directus
   directly. (b) **Kiosk-local cache** on each Pi / repurposed legacy PC: every kiosk has
   real local storage, so it keeps showing its last-known-good content through a network
   or server outage and degrades gracefully instead of going blank. Cache-invalidation
   mechanism (Directus publish webhook vs. poll) and staleness window still to be set in
   the architecture stage.

4. **Multi-museum tenancy → one deployment per museum (Option A). RESOLVED.**
   Each museum runs its own ExhibitOS + Directus stack on its own hardware; data is fully
   isolated per museum. "Generic platform" means *the same open-source code anyone can
   deploy*, not one shared instance hosting many museums. **Consequence: the schema stays
   single-museum — no `museum` scoping field is added to collections.** This removes
   tenancy complexity from the build entirely.

### 9b. Still Open

5. **Auth model between ExhibitOS and Directus.** A **static read-only Directus API
   token** scoped to published content (simple, recommended for v1) vs. a service account
   with a rotating token vs. Directus's role-based API keys. Also: should the ExhibitOS
   dashboard's admin auth and Directus's user accounts be unified (SSO) or kept separate
   (two logins)? Separate is simpler for v1; unified is nicer for volunteers long-term.

6. **Where does device registration canonically live?** §5.5 mirrors devices into
   Directus for authoring convenience, but live fleet state lives in ExhibitOS SQLite.
   Decide whether `display_device` exists in Directus at all, or whether the dashboard is
   the sole SoR for devices and authors assign content to *rooms* rather than to specific
   devices. Leaning: devices live only in ExhibitOS; authors assign to rooms.

7. **Directus revenue-tier compliance.** The free self-hosted tier is conditioned on the
   deploying org being under $5M revenue. Confirm InfoAge / VCF qualifies, and document
   the licensing posture for downstream museums that adopt ExhibitOS.

8. **Form-per-asset vs. form-per-assignment overrides.** `asset.card_template` and
   `display_device.default_form` both influence rendering. Decide the precedence rules
   when an assignment specifies a form different from the device default (e.g. can a
   curator force a card onto a video-default screen for a day?).

---

## 10. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-05-31 | Nick DeMarco (AI-assisted) | Initial first draft. Locked decisions documented (Directus as SoR, ExhibitOS as renderer+fleet, four v1 forms, 3280 first exhibit). |
| 0.2 | 2026-05-31 | Nick DeMarco (AI-assisted) | Resolved 4 open questions (§9a): Playwright card export; configurable `qr_base_url` + per-exhibit slug; two-tier cache (server mirror + kiosk-local); one-deployment-per-museum tenancy (schema stays single-museum). |
| 0.3 | 2026-06-01 | Nick DeMarco (AI-assisted) | Kept original link-target wiki architecture (no publish-to-wiki, no public-deep-page render target). **Kiosk video policy:** kiosks play self-hosted HTML5 `<video>` only — no YouTube iframe on kiosks (public-kiosk escape risk); YouTube reserved for phone/QR deep page. Added kiosk URL-allowlist navigation lockdown (issue #37). Media mirror now holds video binaries. |
