# Technical Architecture: ExhibitOS

> **Content architecture:** the docent wiki is the source of truth — see
> [`decisions/0001-content-source.md`](decisions/0001-content-source.md) (a CMS was explored and
> passed on). The render, fleet, Display Profile, caching, and deployment sections describe
> ExhibitOS directly.

**Version:** 0.3
**Last Updated:** 2026-06-05
**Author:** Software Architecture (AI-assisted), for Nick DeMarco
**Status:** Draft — for review
**PRD Reference:** [`docs/PRD.md`](./PRD.md) v0.4
**Repo:** `github.com/nickdnj/exhibit-os` · local `~/Workspaces/exhibit-os`

---

## 0. How to read this document

This architecture is **prescriptive enough to scaffold from.** The `Exhibit` read-cache
model and the wiki-ingest path (§4–§5) match the built code. The refactor map (§9) names
real files in the seeded repo. The deployment topology (§10) is concrete Docker Compose.

Everything here respects the **locked decisions** in PRD §9a (docent wiki as system of
record, source-order ordering, idempotent re-ingest, Playwright print, configurable QR,
two-tier cache, one-deployment-per-museum). It does **not** re-open the content-source
decision (ADR-0001).

---

## 1. Architecture Overview

ExhibitOS is a **single-service system** behind one mini PC, fed by the museum's existing
docent wiki, with a fleet of dumb web clients hanging off it. The defining principle is a hard
separation between **content authoring** (owned by the docent wiki) and **ingest + presentation
+ fleet control** (owned by ExhibitOS):

- **The docent wiki (DokuWiki)** is the **system of record (SoR)** for ALL narrative content —
  title, interpretive text, key facts, people, year, relationships — and its revision history.
  Docents author and edit there, as they do today; the wiki provides accounts, drafts, diffs,
  attribution, and revert.
- **ExhibitOS** (the refactored SignBoard core: FastAPI + React + SQLite + WebSocket)
  **ingests** the wiki into a local **`Exhibit` read-cache**, renders content by device class,
  exports printable cards via Playwright, and controls the physical fleet. It authors **no
  narrative content** — only display-assignment config, the deliverable display assets
  (hero image, video, deep-link, location), and the read-cache.

Displays **never re-parse the wiki.** They read ExhibitOS's local read-cache. A wiki outage
never blanks the gallery — the read-cache keeps serving the last ingested content; the kiosk
Service Worker (tier 2) keeps serving through a server/LAN outage.

### 1.1 Component diagram (text)

```
┌───────────────────────────────────────────────────────────────────────────┐
│ AUTHORING (Docents — in the wiki they already use)                          │
│   DokuWiki  (System of Record)                                              │
│   accounts · page revisions · diffs · attribution · revert                  │
│   exhibit pages: title · interpretive text · key facts · people · year       │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │  ingest: DokuWiki export FILE (today)
                           │          / live DokuWiki API (later, same parser)
                           ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ EXHIBITOS SERVER  (mini PC, Docker)  — INGEST · RENDER · FLEET               │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ WIKI-INGEST SERVICE  (services/wiki_ingest.py)                         │ │
│   │   parse DokuWiki export → idempotent upsert by slug (content_hash)     │ │
│   │   refresh wiki-sourced fields on change; PRESERVE ExhibitOS-owned      │ │
│   │   display fields; source order → sort_order → display order            │ │
│   │   trigger: POST /api/exhibits/ingest (auth) · scripts.ingest_wiki CLI  │ │
│   └───────────────────────┬──────────────────────────────────────────────┘ │
│                           ▼                                                   │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ EXHIBIT READ-CACHE (SQLite)     DISPLAY-ASSIGNMENT CONFIG (SQLite)       │ │
│   │  exhibits (ingested wiki        display_device · display_assignment      │ │
│   │  content + ExhibitOS-owned      overlay · schedule · setting             │ │
│   │  display fields)                (repurposed SignBoard Page/Channel)      │ │
│   │  media files on disk                                                     │ │
│   └───────────────────────┬──────────────────────────────────────────────┘ │
│                           ▼                                                   │
│   ┌─────────────┬──────────────┬──────────────┬─────────────────────────┐  │
│   │ Renderer:   │ Renderer:    │ Renderer:    │ DASHBOARD (admin React) │  │
│   │ Card + QR   │ Video        │ Touch        │  assign · schedule ·    │  │
│   │ (+ Playwright│ display     │ interactive  │  overlay · print export │  │
│   │  print)     │              │ (touch class)│  · FLEET tab            │  │
│   └─────────────┴──────────────┴──────────────┴─────────────┬───────────┘  │
│         served at  GET /display/<room-slug>                  │              │
└──────────┬────────────────────────────────────┬─────────────┴──────────────┘
   WebSocket push (Pi)              Fully Kiosk REST pull (TV/stick)   admin JWT
           ▼                                     ▼
┌────────────────────────┐         ┌──────────────────────────────────┐
│ Pi Zero 2 W kiosk      │         │ Onn FHD stick / Google TV         │
│ Chromium + exhibit-    │         │ Fully Kiosk Browser, REST :2323   │
│ agent (WS heartbeat)   │         │ (no agent; dashboard polls/pushes)│
│ tier-2 cache:          │         │ tier-2 cache: Chromium HTTP cache │
│  Chromium HTTP cache + │         │  + Service Worker                 │
│  Service Worker        │         └──────────────────────────────────┘
│ GET /display/<room>    │
│ Legacy PC kiosk = same as Pi (Chromium + agent), x86 build of agent  │
└────────────────────────┘
                           │
                           ▼
                 Visitor phone (QR) ──▶ {qr_base_url}/{slug}
                 (deep content: wiki entry + embedded YouTube)
```

### 1.2 The contract (one sentence)

**The docent wiki is the only place narrative content is authored; ExhibitOS is the only
place displays are configured and controlled; ExhibitOS ingests the wiki one-way into a local
read-cache (on-demand re-ingest today; live API later) and never writes back to the wiki.**

---

## 2. Key Architectural Decisions (summary table)

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Content system of record | **The docent wiki (DokuWiki)** — ExhibitOS ingests it | ADR-0001. Don't run a CMS; reuse the docents' tool + its revision control. |
| D2 | Content ingest model | **Idempotent upsert by `slug` via `content_hash`** into the SQLite `Exhibit` read-cache; ExhibitOS-owned display fields preserved across re-ingest | Re-ingest any number of times safely; narrative refreshes only when the source changes. (§5) |
| D3 | Display order | **Source order (`sort_order`) from the wiki export**, not parsed year | The source is in approximate chronological order; parsed "years" are often model numbers. (§5) |
| D4 | `display_device` location | **ExhibitOS only; authors assign to *rooms*** | Devices are physical/fleet state, not content. (§3.2) |
| D5 | Form precedence | **assignment form > device `default_form`**, gated by `device_class` | Resolved. (§3.3) |
| D6 | Re-ingest trigger | **On-demand (admin Re-ingest button / `scripts.ingest_wiki` CLI) today; scheduled / live DokuWiki API later** | Manual file ingest is enough for v1; same parser will feed the live API. (§5) |
| D7 | Card print pipeline | **Playwright headless Chromium, server-side** | PRD-locked. One HTML/CSS template → pixel-identical screen + print. |
| D8 | QR resolution | **`{qr_base_url}/{slug}`** + per-exhibit `deep_content_url` override | PRD-locked. |
| D9 | Fleet protocol | **Two protocols, bridged not unified** (Pi=WS push, FullyKiosk=REST pull) | PRD-locked; inherited from SignBoard fleet specs verbatim. |
| D10 | Tenancy | **One deployment per museum; no museum-scoping field** | PRD-locked. |
| D11 | Tier-2 kiosk cache | **Service Worker (Pi/legacy PC) + Chromium HTTP cache** | Real local storage on each kiosk; survives server/network outage. (§5.3) |
| D12 | **Display Profile** (per physical display) | **Profile in the ExhibitOS `display_device` registry** drives a render path = `{transport} × {orientation layout} × {text-scale from physical size + distance} × {class-allowed forms}`. Auto-detected screen metrics + manual physical size. | New 2026-06-01 decision. One profile per screen so identical content renders correctly on a 24″ desk monitor, a portrait wall sign, and a 75″ 4K TV without per-device code. (§6a) |

### 2.1 Technology stack

| Layer | Technology |
|---|---|
| Content SoR | The museum's existing docent wiki (DokuWiki) — external to ExhibitOS |
| ExhibitOS API / ingest / fleet | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0, httpx |
| Card print | Playwright (Python) + bundled Chromium |
| Dashboard + display clients | React 19, React Router 7, Tailwind 4, Vite 8 |
| ExhibitOS store | SQLite (`Exhibit` read-cache + assignment config) |
| Media mirror | Local filesystem volume on mini PC |
| Fleet | WebSocket (Pi/legacy PC agent) + Fully Kiosk REST :2323 (TV/stick) |
| Containerization | Docker Compose on the mini PC (single ExhibitOS service) |
| QR | `qrcode[pil]` (already stubbed in requirements.txt) |

---

## 3. Resolved Open Questions

### 3.1 Wiki access for ingest → read-only path, file today / API later

**Decision.** ExhibitOS reads the docent wiki **one-way, read-only**. It never authenticates
to write, and never writes back. Two ingest sources feed the **same parser**
(`parse_dokuwiki()`):

- **v1 — a DokuWiki export FILE.** The wiki is exported (the `the_artifacts` dump → 108
  structured exhibits today) to a path ExhibitOS reads (`WIKI_EXPORT_PATH`, default
  `data/wiki-export/the_artifacts.txt`). Re-ingest is triggered on demand — the authed
  `POST /api/exhibits/ingest` (dashboard Re-ingest) or `python -m scripts.ingest_wiki`.
- **Later — the live DokuWiki API** (XML-RPC/REST) with a read-only docent account, on a
  schedule. The wiki is login-gated, so this uses an authenticated *read* path; the parser
  and upsert logic are unchanged.

**No tokens to a CMS, no write-back, no SSO problem.** Because authoring stays in the wiki and
ExhibitOS only reads, there is no "two logins" or identity-provider question: docents log into
the wiki they already use; the single infra admin logs into the ExhibitOS dashboard (JWT, the
SignBoard `admin_user` table) to manage displays and trigger re-ingest. A leaked dashboard
credential exposes display config only — never the authoring system.

> **Open item (PRD §9b / OPEN-QUESTIONS §2):** the visitor "deep-dive" QR target needs a
> *public* page because the docents' wiki is gated. Either ExhibitOS hosts the public deep page
> or VCF opens a public wiki section.

### 3.2 Where `display_device` lives → ExhibitOS only; authors assign to rooms

**Decision.** Devices live **only** in ExhibitOS. They are physical fleet state
(online/offline, IP, heartbeat, platform, class) — not content, and not something the wiki
knows about. They live in the ExhibitOS SQLite `display_device` table (the renamed/extended
SignBoard `kiosks` table).

**Consequence for authoring.** Authors **assign content to rooms, not to devices.** A room is
an ExhibitOS concept used for display routing and assignment (a named feed with a slug). The
ExhibitOS dashboard maps rooms → physical devices. So the author's mental model is "this
exhibit shows in the Main Gallery"; the admin's model is "the Main Gallery has a passive card
display (Pi) and a touchscreen (Onn)." Each device is bound to exactly one room and renders
that room's feed in the device's form.

**Why this is right:**
- Keeps fleet churn (a Pi dies, gets reflashed, gets a new IP) out of the content path
  entirely — nothing about a device touches the wiki or the `Exhibit` read-cache.
- Matches the personas: Doug thinks in rooms and exhibits; Nick thinks in devices.

The room slug is the feed key used in the display URL `/display/<room-slug>`, preserving
SignBoard's subscribe-by-slug model.

### 3.3 Form precedence: per-exhibit vs per-assignment → assignment wins, gated by class

Three things influence what renders on a screen: the **card template** (a *style* hint,
not a form), the device's `default_form`, and the **assignment's** chosen form. Rules:

1. **Form is chosen at assignment time and wins over `default_form`.** When a curator
   assigns content to a room/device, they pick the form (`card` / `video` /
   `interactive`). That assignment-level form is authoritative. `default_form` is only
   the fallback used when content is assigned to a *room* generically without a per-device
   form override (the device renders the room feed in its own `default_form`).
2. **`device_class` is a hard gate that overrides everything.** A `passive` device can
   **never** render `interactive`, even if an assignment requests it. The renderer
   enforces this server-side and the dashboard warns at assignment time. A passive device
   handed `interactive` falls back to its `default_form` and logs an error state.
3. **The card template is orthogonal** — it selects *which* card style/print template
   (`infoage-house`, etc.) to use *when* the form is `card`. It never selects a form.

So: **`device_class` (gate) → assignment form (if present and allowed) → `default_form`
(fallback) → card template (style, only when form=card).** This lets a curator "force a
card onto a video-default screen for a day" simply by making an assignment with `form=card`;
it does not let them force interactive onto a passive panel.

---

## 4. The `Exhibit` Read-Cache Model (matches the built code)

Narrative content is authored in the docent wiki. ExhibitOS holds it in **one SQLite model,
`Exhibit`** (`server/models/exhibit.py`), populated by wiki ingest (§5). There is **no CMS and
no separate collections** for rooms/people/media as content tables: rooms are an ExhibitOS
display-routing concept (§3.2), people arrive as a wiki-sourced field, and deliverable media are
ExhibitOS-owned display fields on `Exhibit`.

> **Single-museum (D10):** no museum-scoping field.

### 4.1 `Exhibit` — the one model

Fields split into **wiki-sourced** (refreshed on re-ingest only when `content_hash` changes) and
**ExhibitOS-owned** (set in the dashboard, **never** overwritten by re-ingest). This table
mirrors the built SQLAlchemy model exactly.

| Field | Type | Origin | Constraints / notes |
|---|---|---|---|
| `id` | int (PK, autoincrement) | system | |
| `slug` | str(200), unique, indexed | derived | url-safe id from the title, e.g. `concurrent-3280`; identically-titled exhibits get a stable `-2`/`-3` suffix |
| `title` | str(300) | **wiki** | "The Concurrent 3280" |
| `year_introduced` | int, nullable | **wiki** | earliest plausible year parsed from body/title (floor 1900 — pre-1900 "years" are usually model numbers); display order does **not** rely on it |
| `sort_order` | int, default 0, indexed | **wiki** | source position in the export → **drives display order** |
| `body_text` | text, default "" | **wiki** | interpretive narrative (blank-line-collapsed) |
| `key_facts` | text, default "" | **wiki** | newline-joined bullet facts |
| `people` | str(500), nullable | **wiki** | people associated with the exhibit (when present in the source) |
| `related_exhibits` | text, nullable | **wiki/ExhibitOS** | cross-reference links (the 3280 ↔ Onyx 10000 case); ExhibitOS-managed until the wiki carries them |
| `source_ref` | str(300) | derived | provenance, e.g. `the_artifacts#<slug>` |
| `content_hash` | str(64) | derived | SHA-256 over the wiki-sourced fields; **idempotency key** for re-ingest |
| `ingested_at` | datetime | derived | last ingest timestamp |
| `hero_image` | str(500), nullable | **ExhibitOS** | deliverable asset — **preserved across re-ingest** |
| `video_url` | str(500), nullable | **ExhibitOS** | self-hosted looping video — **preserved across re-ingest** |
| `deep_content_url` | str(500), nullable | **ExhibitOS** | QR/phone deep-dive target — **preserved across re-ingest** |
| `location` | str(200), nullable | **ExhibitOS** | physical location / room reference — **preserved across re-ingest** |

### 4.2 Rooms, people, related links, media

- **Rooms / display feeds** are an ExhibitOS concept used for fleet routing
  (`/display/<room-slug>`) and assignment — not a content collection. The dashboard maps rooms
  → physical devices (§3.2).
- **People** is a wiki-sourced string field on `Exhibit`, populated when the source provides it.
  Structured person records are a future enhancement, not a v1 content table.
- **Related-exhibit links** live in the `related_exhibits` field (ExhibitOS-managed), keyed to
  exhibit slug. ExhibitOS renders them as "see also"; reciprocal links are explicit, not
  auto-mirrored.
- **Deliverable media** (hero image, looping video) are ExhibitOS-owned display fields, set in
  the dashboard and preserved across re-ingest. The wiki stays the source for narrative text;
  ExhibitOS owns the on-floor assets the wiki doesn't naturally hold.

### 4.3 Settings

`qr_base_url` and similar platform settings live in the ExhibitOS `setting` SQLite table
(reused from SignBoard) — there is no separate content store. The QR for an exhibit resolves to
`{qr_base_url}/{slug}`, unless the exhibit's ExhibitOS-owned `deep_content_url` overrides it.

### 4.4 Provenance, idempotency, and order (why these fields exist)

- **`content_hash`** is a stable hash of the wiki-sourced fields only. On re-ingest, an exhibit
  whose hash is unchanged is skipped (its `sort_order` is still refreshed); a changed hash
  refreshes the wiki-sourced fields and **never** touches the ExhibitOS-owned display fields.
- **`source_ref`** records where the exhibit came from in the source for traceability.
- **`sort_order`** comes from the exhibit's position in the export, which is in approximate
  chronological order — more reliable than the parsed year for driving the display tour (D3).

---

## 5. Wiki Ingest, Read-Cache & Two-Tier Resilience

### 5.1 Authoring → ingest → render (end to end)

```
1. A docent edits the artifact's page in the wiki (the tool they already use);
   the wiki records the revision, diff, attribution.
2. The wiki content reaches ExhibitOS as input to one parser:
     - v1:    a DokuWiki export FILE at WIKI_EXPORT_PATH
     - later: the live DokuWiki API (XML-RPC/REST) — same parse_dokuwiki()
3. Re-ingest is triggered:
     - admin clicks "Re-ingest" → POST /api/exhibits/ingest  (authed)
     - or CLI: python -m scripts.ingest_wiki
     - or (later) a schedule
4. wiki_ingest.ingest_from_file():
     a. parse_dokuwiki(text) → structured exhibit dicts (title, body_text,
        key_facts, people, year, slug, source_ref, sort_order).
     b. For each, compute content_hash over the wiki-sourced fields.
     c. Upsert by slug into the SQLite `exhibits` table:
          new slug          → insert (wiki fields + empty ExhibitOS-owned fields)
          changed hash       → refresh wiki-sourced fields ONLY
          unchanged          → keep sort_order current, otherwise skip
        ExhibitOS-owned display fields (hero_image / video_url /
        deep_content_url / location) are NEVER overwritten.
     d. Return counts {created, updated, unchanged, total} to the caller.
5. Displays read GET /api/exhibits and /api/exhibits/{slug} (served from the
   `exhibits` read-cache, in sort_order). On re-ingest, ExhibitOS notifies
   affected displays via WebSocket (notify_content_changed); kiosks refetch.
6. Kiosk renders; Service Worker updates its tier-2 cache for offline use.
```

### 5.2 Idempotency & ordering — D2/D3

- **Idempotent upsert by slug via `content_hash`.** The hash covers the wiki-sourced fields
  only (title, body, key facts, people, year, related). An unchanged exhibit is a no-op
  (beyond keeping `sort_order` current); a changed one refreshes its narrative. Re-ingest is
  safe to run any number of times — the built `ingest_from_file()` proves this on the
  `the_artifacts` dump (108 exhibits).
- **ExhibitOS-owned fields survive re-ingest.** `hero_image`, `video_url`, `deep_content_url`,
  `location` are set in the dashboard and are **never** clobbered when the wiki content
  refreshes — so re-ingesting an edited placard doesn't drop the hero photo a curator attached.
- **Source order drives display order.** `sort_order` = the exhibit's position in the export
  (approximate chronological); the public list (`GET /api/exhibits`) and the auto-rotating
  `/show` tour render in that order.
- **Staleness window is whatever the re-ingest cadence is.** v1 is on-demand (admin button /
  CLI); a "fix a typo" updates the displays on the next ingest. The live-API phase will close
  this to a schedule. There is no webhook/poll machinery — the wiki isn't asked to call us.

### 5.3 Two-tier resilience, concretely

**Tier 1 — ExhibitOS server-side read-cache (the mini PC).** The authoritative copy *for
displays*:

- the `exhibits` SQLite table (the `Exhibit` read-cache, §4) — renderers read from here, never
  re-parse the wiki at render time;
- `/data/media` filesystem store for deliverable binaries (hero images, self-hosted video),
  served by ExhibitOS at `/media/<id>` (replaces SignBoard's `/uploads`);
- Result: **if the wiki is unreachable, displays keep working** off the last ingested content.
  **No demo/placeholder content, ever** (PRD §8.3, feedback `no-demo-fallback`): if the
  read-cache has no content for a room, the display shows a clear error state.

**Tier 2 — kiosk-local cache (each Pi / legacy PC / TV).** Each kiosk degrades gracefully
through a *network or server* outage:

- **Pi / legacy PC (Chromium):** the React display app ships a **Service Worker**
  (via `vite-plugin-pwa`) with a cache-first strategy for `/api/exhibits*`, `/api/display/<room>`
  and `/media/*`. On load it caches the feed JSON + media; if the mini PC or LAN drops, it
  serves the last-known-good render from local disk, revalidating on reconnect
  (stale-while-revalidate). Pi has SD-card storage; legacy PCs have disk.
- **Onn stick / Google TV (Fully Kiosk):** relies on Fully Kiosk's built-in webview HTTP
  cache plus the same Service Worker (Fully Kiosk runs Chromium and supports SWs). Fully
  Kiosk's "reload on network reconnect" handles re-sync.
- **Staleness signal:** the display footer shows a subtle "offline — last updated HH:MM"
  indicator when the Service Worker is serving cached content, so staff can tell a frozen
  screen from a genuinely-cached one.

> **Three layers of resilience.** Wiki unreachable → Tier 1 read-cache serves (re-ingest
> resumes when it's back). Mini PC/LAN down → Tier 2 serves. Only a kiosk-local failure
> (power, hardware) blanks a single screen, recoverable from the Fleet tab.

---

## 6. Fleet / Device Protocol

ExhibitOS inherits SignBoard's **two-protocol, bridged-not-unified** fleet model verbatim
(`signboard-fleet-management-spec.md`, `signboard-google-tv-spec.md`). The domain changes
are: renaming, the addition of `device_class`, and the per-display **Display Profile**
(§6a) — which the agent/served-page report on connect (§6a.4). Note `platform` values are
`chromium-kiosk` / `fully-kiosk` (§6.2 rename note); they select transport only.

### 6.1 Device classes

| `device_class` | Renders | Hardware | Platform / transport |
|---|---|---|---|
| `passive` | `card` or `video` | Pi Zero 2 W + monitor; legacy PC + monitor; Onn stick + TV; Google TV | `chromium-kiosk` (Pi/legacy = WS); `fully-kiosk` (stick/TV = REST) |
| `touchscreen` | `interactive` (also can do card/video) | touch panel driven by a Pi/legacy PC (Chromium touch) | `chromium-kiosk` (touch needs the agent + local browser) |

`device_class` gates the interactive form (D5/§3.3). `platform` (`chromium-kiosk` /
`fully-kiosk`) selects the fleet transport + provisioning only — never the renderer. The
full per-display **Display Profile** (resolution, orientation, DPR, physical size, viewing
distance, class) and its render-path logic are specified in **§6a**.

### 6.2 `display_device` table (ExhibitOS SQLite — renamed/extended SignBoard `kiosks`)

| column | type | notes |
|---|---|---|
| `id` | TEXT PK | hostname, e.g. `exhibit-main-gallery-card` |
| `room_slug` | TEXT | the room feed it subscribes to (replaces `channel_slug`) |
| `name` | TEXT | "Main Gallery — left wall" |
| `device_class` | TEXT | `passive` / `touchscreen` — **profile field**, gates allowed forms (§3.3) |
| `platform` | TEXT | `chromium-kiosk` / `fully-kiosk` — **profile field**, selects fleet transport + provisioning only (§6a.1) |
| `default_form` | TEXT | `card` / `video` / `interactive` |
| `assignment_form` | TEXT NULL | per-device form override (see §3.3) |
| `fully_kiosk_ip` | TEXT NULL | for `fully-kiosk` platform |
| **`resolution_w`** | **INTEGER NULL** | **profile — screen width in CSS px; auto-detected (§6a.4)** |
| **`resolution_h`** | **INTEGER NULL** | **profile — screen height in CSS px; auto-detected** |
| **`orientation`** | **TEXT NULL** | **profile — `landscape` / `portrait`; auto-detected (derived from w/h), manually overridable** |
| **`device_pixel_ratio`** | **REAL NULL** | **profile — `window.devicePixelRatio`; auto-detected** |
| **`physical_size_in`** | **REAL NULL** | **profile — diagonal in inches; MANUAL (browser can't know it)** |
| **`viewing_distance_ft`** | **REAL NULL** | **profile — typical viewer distance in feet; MANUAL** |
| **`profile_detected_at`** | **INTEGER NULL** | **epoch secs of last auto-detect handshake** |
| `ip` | TEXT | last seen |
| `version` | TEXT | git short-SHA reported by agent |
| `online` | INTEGER | 0/1, computed from heartbeat/poll |
| `last_heartbeat` | INTEGER | epoch seconds |
| `uptime_seconds` / `memory_free_mb` / `load_avg_1m` | — | reported by Pi agent |
| `off_channel` | INTEGER | 0/1, Fully Kiosk URL drift flag (§6.4) |
| `status` | TEXT | `active` / `maintenance` / `retired` |
| `created_at` | INTEGER | |

> **`platform` value rename (2026-06-01).** The two platforms are now named for what
> they actually are: **`chromium-kiosk`** (Pi / legacy PC running Chromium + `exhibit-agent`
> over WebSocket) and **`fully-kiosk`** (Onn stick / Google TV running Fully Kiosk over
> REST). `legacy-pc` is folded into `chromium-kiosk` (it is a Chromium kiosk on x86 — same
> transport, same agent). Platform selects **only** the fleet transport and provisioning
> path; it never changes the rendering engine, which is "everything is a web view."

### 6.3 Pi / legacy PC → WebSocket push (`exhibit-agent`)

Renamed from `signboard-agent`. Small persistent Python client, systemd
`exhibit-agent.service` (`Restart=always`). On boot reads
`/boot/firmware/exhibit.conf` (`HOSTNAME`, `DISPLAY_URL`, derives server base). Opens
persistent WS to `WS /ws/device-agent` with `Authorization: Bearer <DEVICE_AGENT_TOKEN>`.
Sends 10s heartbeat `{hostname, ip, version, uptime, mem_free, load_avg}`. Handles
commands: `reboot` (`/sbin/reboot`), `reload` (`pkill chromium`; service auto-restarts),
`update-scripts` (`git pull` from pinned repo/branch + restart). Server keeps in-memory
`dict[hostname → WebSocket]`. Legacy PC uses the same agent with an x86 build/venv.

### 6.4 Onn stick / Google TV → Fully Kiosk REST pull

No on-device agent. The dashboard polls each device's Fully Kiosk Remote Admin REST
(`http://<ip>:2323/`, **LAN-only**) every 30s for `deviceInfo`, and issues commands on
demand: `loadURL`, `restartApp`, `rebootDevice`, `getScreenshot`, `screenOn`/`screenOff`.
Per-device Fully Kiosk password stored masked in the ExhibitOS `setting` store.

### 6.5 Bridged in the dashboard, not unified

Per the SignBoard design decision (quoted): the two protocols have fundamentally
different remote-access models; the Fleet tab presents one table but routes each action
by `platform`. Commands available per platform:

| Action | Pi / legacy PC (WS) | Fully Kiosk (REST) |
|---|---|---|
| Reboot | `reboot` frame | `rebootDevice` |
| Reload | `reload` frame | `restartApp` + `loadURL` |
| Update | `update-scripts` frame | n/a (Fully Kiosk auto-updates; lock recommended) |
| Screenshot | n/a | `getScreenshot` |
| Screen on/off | (HDMI-CEC via agent, optional) | `screenOn` / `screenOff` |
| Assign content / "Reload to correct URL" | server changes assignment → WS `content_changed` | `loadURL` to `/display/<room>` |

Error handling carried forward: unreachable → mark offline, keep last-known status,
retry; URL drift → flag "off channel" + one-click "Reload to correct URL."

### 6.6 Assign-content command path

A curator assigns an asset/room-feed + form to a device in the dashboard. ExhibitOS
writes the `display_assignment` row (§9.1), then:
- **Pi/touch:** `ws_manager.notify_content_changed(room_slug)` → kiosk refetches
  `/api/display/<room>` and re-renders.
- **Fully Kiosk:** if the device's current URL differs from `/display/<room>`, the server
  issues `loadURL`; otherwise the kiosk's own refetch picks it up. Broadcast + rate
  limiting + confirmation modals carried from the fleet spec.

---

## 6a. Display Profile & Render Path (2026-06-01)

> **Decision note (2026-06-01).** ExhibitOS gains a first-class **Display Profile** per
> physical display, stored in the ExhibitOS `display_device` registry (D4/D12 — a profile is
> fleet/hardware state, not content). The profile is the single input that determines how one
> exhibit renders on any given screen, so identical content is correct on a 24″ desk monitor, a
> portrait wall sign, and a 75″ 4K lobby TV without per-device code. **Full portrait support
> ships in v1** (the interpretive card has a distinct portrait composition, not a rotated
> landscape).

### 6a.1 The Display Profile (fields)

Per physical display, in `display_device` (§6.2):

| Field | Type | Source | Meaning |
|---|---|---|---|
| `platform` | `chromium-kiosk` \| `fully-kiosk` | set at registration | fleet **transport + provisioning only** — not the renderer |
| `device_class` | `passive` \| `touch` | set at registration | **hard gate** on allowed forms (§3.3); `touch` ⇒ may render `interactive` |
| `resolution_w` × `resolution_h` | px | **auto-detected** | CSS-pixel screen size the browser reports |
| `orientation` | `landscape` \| `portrait` | **auto-detected** (derived `w<h ⇒ portrait`), manual override allowed | selects the **card layout variant** |
| `device_pixel_ratio` | float | **auto-detected** | `window.devicePixelRatio`; informs asset/QR raster sizing (4K = DPR 2 at 1080 CSS px) |
| `physical_size_in` | inches (diagonal) | **MANUAL** (dashboard) | browser cannot know it; drives text scale |
| `viewing_distance_ft` | feet | **MANUAL** (dashboard) | typical viewer standoff; drives text scale |

### 6a.2 Render path — the decision logic

The profile resolves to a render path with four orthogonal axes:

```
render_path(profile, assignment, asset) =
  1. TRANSPORT       = profile.platform        # chromium-kiosk → WS push ; fully-kiosk → REST pull
                                               #   (affects sync/refresh delivery ONLY, not the DOM)
  2. FORM            = gate(device_class) → assignment.form → device.default_form → (card_template if card)
                                               #   unchanged precedence from §3.3
  3. LAYOUT VARIANT  = by FORM:
       • card  → orientation == 'portrait' ? CARD_PORTRAIT : CARD_LANDSCAPE
                 (fixed designed canvas, scaled-to-fit; letterbox/pillarbox OK — §7.1)
       • video → RESPONSIVE  (object-fit: contain to actual viewport — §7.2, no fixed canvas)
       • interactive → RESPONSIVE  (fluid grid to actual viewport — §7.3, no fixed canvas)
  4. ROOT TEXT SCALE = text_scale(physical_size_in, viewing_distance_ft)   # §6a.3
                       applied as the CSS root rem on EVERY form
```

- **Form precedence is unchanged** (§3.3): `device_class` hard gate → assignment form →
  device `default_form` → `card_template` (style, when form=card). The profile adds the
  **orientation** and **text-scale** axes; it does not re-open form precedence.
- **Transport is decoupled from rendering.** A `chromium-kiosk` and a `fully-kiosk` showing
  the same portrait card render byte-identical DOM; they differ only in how a content change
  reaches them (WS `content_changed` push vs. the kiosk's own REST refetch).

### 6a.3 Text legibility scales from physical size + viewing distance (not pixels)

A pixel size that is legible on a 24″ monitor at a desk is **illegible** on a 75″ TV viewed
from across a gallery, even though both are "1080p". Legibility is governed by the **visual
angle** the text subtends at the viewer's eye, which depends on physical glyph height and
viewing distance — not CSS pixels. ExhibitOS therefore computes a **root rem scale** from
the profile and sets it as the CSS root font size; all type (which is authored in `rem`)
scales coherently.

**Baseline.** The existing ADA / distance-viewing minimums (UX-SPEC §8.1) are defined as
correct on a **reference display: 24″ diagonal viewed at 5 ft**. We preserve those minimums
exactly at the baseline and scale relative to it.

**Formula.**

```
# Physical height of one CSS px on this screen (proportional to diagonal / hypot(resolution)).
px_height_in(profile)  = profile.physical_size_in / hypot(resolution_w, resolution_h)

# To hold the SAME visual angle as the baseline, on-screen physical glyph height must scale
# with viewing distance. So the rem scale is:
text_scale = (viewing_distance_ft / 5.0)              # farther viewer ⇒ bigger
           × (px_height_in(reference) / px_height_in(profile))   # smaller/denser px ⇒ bigger rem
where reference = 24" diagonal at 1920×1080  ⇒  px_height_in(reference) ≈ 0.01088 in/px

root_rem_px = BASE_REM_PX (= 16) × clamp(text_scale, 0.85, 4.0)
```

Worked examples (BASE_REM_PX = 16, baseline 24″@5ft ⇒ scale 1.0 ⇒ 16px root):

| Display | Diagonal | Resolution | Distance | `text_scale` | root rem |
|---|---|---|---|---|---|
| Reference desk monitor | 24″ | 1920×1080 | 5 ft | 1.00 | 16 px |
| Wall card panel | 43″ | 1920×1080 | 8 ft | ~0.89 (closer in angular terms; clamped ≥0.85) | ~14 px |
| Large lobby TV | 75″ | 3840×2160 (DPR 2) | 15 ft | ~1.71 | ~27 px |
| Portrait corridor sign | 49″ (1080×1920) | portrait | 6 ft | ~1.06 | ~17 px |

> 4K note: `device_pixel_ratio` is **not** in the text-scale math — text scale uses *physical*
> px height (diagonal ÷ resolution hypotenuse), which already accounts for pixel density. DPR
> is used separately to request appropriately-sized raster assets/QR so they stay crisp.

- The card's fixed-canvas scale-to-fit (§7.1) and this root-rem scale **compose**: the canvas
  is scaled geometrically to fit the viewport, and the canvas's *internal* type is authored in
  rem so the legibility floor is honored regardless of canvas-to-viewport ratio. (Responsive
  video/touch use the root rem directly.)
- The clamp floor (0.85) prevents text shrinking below the ADA minimum on small/near displays;
  the ceiling (4.0) prevents absurd sizes on misconfigured profiles. If `physical_size_in` /
  `viewing_distance_ft` are unset, `text_scale = 1.0` (baseline) — never zero, never an error.

### 6a.4 Profile auto-detect handshake (both transports)

Screen metrics (`resolution`, `orientation`, `device_pixel_ratio`) are **auto-detected** by
the browser and reported to ExhibitOS; physical size + viewing distance are **entered
manually** in the dashboard (the browser cannot know them). The detected fields are stored
**read-only** in the dashboard; the manual fields are editable (UX-SPEC §7.4a).

**Common probe payload** (what the browser reports, both transports):

```json
POST /api/devices/{device_id}/profile        (or carried on the WS handshake — below)
{
  "type": "display_profile",
  "resolution_w": 1920,
  "resolution_h": 1080,
  "orientation": "landscape",          // derived: innerWidth < innerHeight ? portrait : landscape
  "device_pixel_ratio": 1.0,           // window.devicePixelRatio
  "screen_w": 1920, "screen_h": 1080,  // window.screen.{width,height} (panel) for sanity vs innerWidth/Height
  "agent_version": "1.0.4"             // present for chromium-kiosk only
}
```
The server merges these into `display_device` (`resolution_w/h`, `orientation`,
`device_pixel_ratio`, `profile_detected_at = now`) and **leaves `physical_size_in` /
`viewing_distance_ft` untouched** (manual fields).

**A) `chromium-kiosk` (Pi / legacy PC) — on the WS device-agent handshake.**
The display page already knows its viewport; the simplest path is for the **served page** to
read `window.innerWidth/innerHeight/devicePixelRatio/screen` and include them in the
`exhibit-agent` connect frame (the agent runs alongside the local Chromium and can read them
from a tiny bridge, or the page POSTs them directly on load — see (C)). Concretely, the agent
adds the profile block to its first `WS /ws/device-agent` message:

```json
// first frame after connect, alongside the existing heartbeat identity
{ "type": "register", "hostname": "exhibit-main-gallery-card",
  "ip": "...", "version": "1.0.4",
  "display_profile": { "resolution_w":1920, "resolution_h":1080,
                       "orientation":"landscape", "device_pixel_ratio":1.0 } }
```
On reconnect or resolution change (`resize`/`orientationchange`), the agent re-sends an
updated `display_profile` frame so a re-cabled or rotated panel self-heals.

**B) `fully-kiosk` (Onn stick / Google TV) — no on-device agent.** Two complementary sources:
- **Coarse, pull:** the dashboard's 30 s Fully Kiosk REST poll (`getDeviceInfo`) returns
  `screenWidth`/`screenHeight`/`screenBrightness` etc.; the bridge maps `screenWidth/Height`
  into `resolution_w/h` as a fallback. (Fully Kiosk reports the **panel**, which on a TV may
  differ from the CSS viewport, so this is the fallback, not the primary.)
- **Accurate, push (primary):** the **served display page itself** carries a tiny JS probe
  (see (C)) that, on load and on `resize`/`orientationchange`, POSTs the common payload to
  `POST /api/devices/{device_id}/profile`. The device id is resolved from the
  `/display/<room-slug>?device_id=…` URL the dashboard assigns (or, if absent, the server
  matches by source IP against the registered Fully Kiosk device). This gives ExhibitOS the
  **true CSS viewport + DPR** of the Fully Kiosk webview without any on-device agent.

**C) The served-page probe (shared by both transports).** `RoomDisplay` mounts a one-shot
profile reporter that fires on first render and on `resize`/`orientationchange` (debounced):

```ts
function reportProfile(deviceId: string) {
  const p = {
    type: "display_profile",
    resolution_w: window.innerWidth,
    resolution_h: window.innerHeight,
    orientation: window.innerWidth < window.innerHeight ? "portrait" : "landscape",
    device_pixel_ratio: window.devicePixelRatio,
    screen_w: window.screen.width, screen_h: window.screen.height,
  };
  navigator.sendBeacon(`/api/devices/${deviceId}/profile`, JSON.stringify(p));
}
```
For `chromium-kiosk` this is redundant with the agent frame (either is sufficient; the page
probe is the universal backstop). For `fully-kiosk` it is the **primary** accurate source.
The probe is best-effort (`sendBeacon`) and never blocks rendering — a missing profile just
means baseline text scale + landscape default until the first report lands.

### 6a.5 Where the profile is consumed

- **`GET /api/display/<room-slug>`** (§7 / issue #15) returns the device's profile fields and
  the resolved `form`, `orientation`, and computed `text_scale` so the renderer needs no
  second round trip. The endpoint resolves the device by `device_id` (query param the
  dashboard bakes into each kiosk URL) or by source IP.
- **`RoomDisplay` / `InfoAgeHouseCard`** (§7.1 / issue #22) pick the portrait vs. landscape
  card canvas from `orientation` and set `:root { font-size: text_scale × 16px }`.
- **Video / touch renderers** (§7.2/§7.3, issues #24/#25) ignore orientation for layout (they
  are fluid) but still apply the root `text_scale` to any overlaid text (titles, captions,
  buttons).

---

## 7. Render Targets — one Exhibit, four forms

All renderers read the **same cached `Exhibit`** from the `exhibits` read-cache (Tier 1). No
renderer re-parses the wiki. Each form is a React route/component under `client/src/display/`,
served at `GET /display/<room-slug>` with the form selected per §3.3 and the **Display Profile**
(§6a) selecting the orientation card layout and the root text scale. (A public interpretive card
also renders at `/exhibit/:slug`, and an auto-rotating collection "show" at `/show`.)

> **Profile-driven render model (2026-06-01).** Two distinct layout strategies, picked by
> form (§6a.2):
> - **Card = fixed designed canvas per orientation, scaled-to-fit.** Two designed canvases —
>   landscape `1920×1080` and portrait `1080×1920` — each a deliberate composition. The
>   active one is chosen by `profile.orientation` and CSS-transform scaled to the actual
>   viewport (letterbox/pillarbox acceptable on odd aspect ratios). This extends the seeded
>   `DisplayCanvas` (which already does `Math.min(w/W, h/H)` scale-to-fit) to accept a
>   `portrait` design size.
> - **Video and touch = responsive to the actual viewport (no fixed canvas).** Video uses
>   `object-fit: contain`; touch is a fluid grid. They adapt to any resolution/orientation
>   without bars.
> - **All forms apply the profile's root `text_scale`** (§6a.3) as the CSS root rem so the
>   ADA legibility floor holds across a 24″ desk monitor and a 75″ wall TV.

### 7.1 Form 1 — Interpretive Card + QR (on-screen AND printable)

- **One shared HTML/CSS template** drives both the on-screen card and the printed sign.
  This is the crux of the Playwright decision (D7): the same Chromium renders both, so
  they cannot drift. The card template (`infoage-house`) is a style hint, not a form.
- **Field mapping** (per PRD §6.1 / the canonical `museum-sign.md` house style), to `Exhibit`
  fields (§4):

| Sign element | Source |
|---|---|
| Title (big blue sans-serif, top-left) | `title` (wiki) |
| Hero photo + caption (upper-left) | `hero_image` (ExhibitOS-owned → `/media/<id>`) |
| Inventor / people credit (upper-right) | `people` (wiki, when present) |
| Bullets | `key_facts` (wiki) |
| "The Backstory:" | `body_text` (wiki) |
| QR + caption (lower-right) | QR(`deep_content_url` if set else `{qr_base_url}/{slug}`) |
| Closer / easter-egg strip | derived from `related_exhibits` (the 3280→Onyx note) |
| Year / dateline | `year_introduced` (wiki) |

- **On-screen:** the `/display/<room>` route renders this template full-screen for a
  `passive`+`card` device, on the **orientation-matched designed canvas** (landscape
  `1920×1080` or portrait `1080×1920`, §6a.2) scaled-to-fit the actual screen. The portrait
  canvas is a **distinct composition** (title / hero+portrait stacked / bullets / backstory /
  QR / closer reflowed tall — UX-SPEC §4.2a), not a rotated landscape. Type inside the canvas
  is authored in `rem`; the root rem is set from `profile.text_scale` (§6a.3) so the ADA floor
  holds at any physical size/distance.
- **Print pipeline:** dashboard "Export printable card" → `POST /api/print/card/<slug>`
  → server runs **Playwright** headless Chromium, navigates to an internal render-only
  route `/_print/card/<slug>?template=infoage-house&orientation=<landscape|portrait>`
  (same template + orientation canvas, print CSS `@page` sized to the InfoAge sign
  dimensions for that orientation), `page.pdf()` → returns the PDF. **Runs server-side on
  the mini PC only** (Chromium bundled in the ExhibitOS image; never on kiosks). The print
  `orientation` defaults to the assigned display's profile orientation but is selectable in
  the export dialog (a curator may print a portrait sign for a screen that happens to be
  landscape, or vice-versa). QR is rendered into the HTML via `qrcode` → data-URI so screen
  and print share one QR.

### 7.2 Form 2 — Video Information Display

- Renders on `passive` + `video`. **Responsive to the actual viewport — no fixed canvas**
  (§6a.2): the `<video>` uses `object-fit: contain` and fills whatever resolution/orientation
  the screen reports, with the player's natural letterbox/pillarbox on aspect mismatch; it
  adapts to portrait or 4K with no app-drawn bars. Any overlaid text (title/room strip,
  captions) is sized by the profile root `text_scale` (§6a.3). Plays the exhibit's
  **self-hosted `video_url`** (an ExhibitOS-owned deliverable asset served from the local
  mirror) via an **HTML5 `<video>` element** (looped, **muted autoplay**, museum-appropriate,
  optional ambient audio per assignment).
  **No YouTube/Vimeo iframe on any kiosk** (2026-06-01 policy): a YouTube embed on a public
  kiosk exposes the "Watch on YouTube" link + suggested-video end cards, letting a visitor
  escape into youtube.com. YouTube is the phone/QR deep-page only. Browser-level navigation
  lockdown is the backstop (§9 / issue #37).
- **Room feed:** if a room (not a single exhibit) is assigned, cycles videos across the
  room's exhibits in `sort_order`. Generalizes SignBoard's `PageCarousel`.
- Honors the room's operating hours for scheduled screen on/off (Pi via agent/HDMI-CEC; Fully
  Kiosk via its schedule). No demo video on missing content — error state.

### 7.3 Form 3 — Touchscreen Interactive

- Renders **only** on `device_class = touchscreen`/`touch` (renderer-enforced gate, §3.3). A
  passive device handed this form refuses it and falls back to `default_form` + logs an
  error state.
- **Responsive to the actual viewport — no fixed canvas** (§6a.2): a fluid grid that reflows
  for landscape, portrait, and 4K touch panels without bars; touch targets and type honor the
  profile root `text_scale` (§6a.3) so the 64–88px target floor stays physically large enough
  at the panel's size/distance.
- Visitor can scroll `body_text`, read `key_facts` and `people`, view any gallery imagery,
  and tap a `related_exhibits` link to jump to the related exhibit's interactive view
  (**3280 → Onyx 10000 traversal** and back).
- Idle timeout → attract/home screen (configurable seconds).

### 7.4 Form 4 — Dashboard (+ Fleet)

- React admin app (refactored SignBoard `client/src/admin/`). Content control: browse
  ingested exhibits (read from the Tier-1 read-cache), set the ExhibitOS-owned display fields
  (hero/video/deep-link/location), trigger a **Re-ingest** from the wiki, assign
  exhibit/room-feed → device with a chosen form, manage schedules + scheduled/emergency
  overlays (carried from SignBoard), trigger printable-card export. Includes a read-only
  "Exhibits" tab listing the ingested exhibits with a Re-ingest action.
- Fleet tab: §6 — live status, per-device Reboot/Reload/Update/Screenshot/Screen, bridged
  by platform, broadcast with confirmation + rate limiting.

---

## 8. Why one template renders both screen and print (the Playwright bet, expanded)

The single highest-value architectural property of ExhibitOS's card is that **the
on-screen card and the printed sign are the same artifact.** Implementation:

- `client/src/display/cards/InfoAgeHouseCard.tsx` is the React component. It is used by
  both the live `/display/<room>` card route and the print-only `/_print/card/<id>` route.
- Print-specific differences (bleed, crop marks, exact mm dimensions, CMYK-safe colors)
  live in a **print stylesheet** toggled by the `/_print/` route, not in a separate
  template. Same DOM, same fonts, same QR.
- `POST /api/print/card/<slug>` (admin) → `services/print_service.py` launches
  Playwright, loads `http://localhost:8100/_print/card/<slug>`, waits for fonts + images +
  QR, calls `page.pdf({format, printBackground:true, ...})`, streams the PDF back.
- Acceptance (PRD §6.1): editing the exhibit's wiki page and re-ingesting changes both the
  live card and the next export with no code change — guaranteed because both read the same
  cached `Exhibit`.

---

## 9. Refactoring the Seeded SignBoard Code

The seeded repo (`~/Workspaces/exhibit-os/server` + `client`) is SignBoard verbatim:
FastAPI + React + Tailwind + SQLite + WebSocket, with Wharfside-specific weather/marine
modules. The refactor has three buckets: **repurpose**, **remove/quarantine**, **rename**.

### 9.1 Repurpose (SignBoard tables/modules → ExhibitOS ingest + assignment + cache)

| SignBoard (today) | ExhibitOS | File-level action |
|---|---|---|
| `models/page.py` (`Page`, holds content body) | **`display_assignment`** — pointer to an `Exhibit` (by slug/id) + form + render options; **no content body** | Replace `Page` with `DisplayAssignment(id, room_slug, exhibit_slug OR room_feed bool, form, render_options_json, sort, is_enabled)`. Drop `config_json`, `image_path`, `page_type`, `is_system`. |
| `models/channel.py` (`Channel`) | **`room` reference** — rooms are an ExhibitOS routing concept; ExhibitOS keeps only the device→room binding | Remove `Channel` as a content table; `room_slug` becomes a column on `display_device` + `display_assignment`. Keep the subscribe-by-slug routing. |
| `models/channel_page.py` (`ChannelPageAssignment`) | folded into `display_assignment` (sort/duration/enabled) | Migrate `sort_order`/`duration_override`/`is_enabled` onto `display_assignment`; delete `channel_page.py`. |
| SQLite content columns | the **`Exhibit` read-cache** (Tier-1; ingested from the wiki) | **Built** — `models/exhibit.py` (the `Exhibit` model, §4). |
| Overlay / schedule tables | **Unchanged** (scheduled + emergency overlays) | Keep — SignBoard's strength, carried forward as-is. (If currently embedded in `announcement`/`page`, extract into a dedicated `overlay` model.) |
| `kiosks` table + agent protocol | **`display_device`** + `device_class`/`platform` | Rename + extend per §6.2. WS manager (`ws/manager.py`, `ws/routes.py`) kept; rename channel→room, add `/ws/device-agent`. |
| `models/admin_user.py` + `api/auth.py` (JWT) | **Unchanged** — dashboard admin auth | Keep as-is for fleet + assignment control + the authed re-ingest trigger. |
| `services/settings_service.py` + `models/setting.py` | **Kept for ExhibitOS settings** (`qr_base_url`, `museum_name`, Fully Kiosk pw, wiki-ingest source path) | Keep as the single settings store; there is no separate content store. |
| `api/pages.py`, `api/channels.py` | **`api/assignments.py`**, **`api/display.py`** | Rewrite: `/api/display/<room-slug>` reads the `Exhibit` read-cache + `display_assignment`; `/api/assignments` is admin CRUD. (`api/exhibits.py` — public list/detail + authed ingest — is **built**.) |
| `client/src/display/PageCarousel.tsx`, `ChannelDisplay.tsx` | **`RoomDisplay.tsx`** + per-form components | Refactor routing to forms; reuse carousel for video room feeds + card sequences. |
| WebSocket `notify_page_update` | **`notify_content_changed(room_slug)`** | Rename; triggered by re-ingest, not by content edits (narrative edits happen in the wiki now). |

### 9.2 Remove / quarantine (Wharfside-specific, no museum use)

Delete these from `server/` (and their routes from `main.py`), and the matching
`client/src/display/*Page.tsx`:

- `services/tempest.py`, `api/weather.py`, `client/src/display/WeatherPage.tsx` — Tempest weather.
- `services/tides.py`, `api/tides.py`, `api/tide_stations.py`, `models/tide_station.py`,
  `client/src/display/TidePage.tsx` — NOAA tides.
- `services/surf.py`, `api/surf.py`, `api/surf_spots.py`, `models/surf_spot.py`,
  `client/src/display/SurfPage.tsx` — surf.
- `services/fishing.py`, `api/fishing.py`, `api/fishing_locations.py`,
  `models/fishing_location.py`, `client/src/display/FishingPage.tsx` — fishing/solunar.
- `services/lightning.py`, `api/lightning.py`, `client/src/display/LightningPage.tsx` —
  lightning alerts.
- Tempest/NOAA/`ephem`/`astral` deps from `requirements.txt`; TagSmart settings
  (`tagsmart_api_url`/`tagsmart_api_key`) from `config.py` + compose.
- Seed functions in `main.py`: `seed_default_channels`, `seed_system_pages`,
  `seed_tide_stations`, `seed_fishing_locations`, `seed_surf_spots` — **deleted, not
  migrated** (PRD §4.4: never fall back to demo data).

**Quarantine vs delete:** prefer **delete** (clean snapshot fork, MIT, no Wharfside
liability). The `AnnouncementPage`/overlay machinery is the one piece to **keep** —
emergency/scheduled overlays generalize to museum use (closures, special events).

### 9.3 Rename scope (SignBoard → ExhibitOS)

- App title/metadata: `main.py` `FastAPI(title="ExhibitOS", description="Museum
  information-display platform")`; logger name `signboard` → `exhibitos`.
- DB file: `signboard.db` → `exhibitos.db`; default admin password env; `signboard_data`
  volume → `exhibitos_data`; `/uploads` → `/media`.
- Agent: `signboard-agent` → `exhibit-agent`; `/boot/firmware/signboard.conf` →
  `exhibit.conf`; systemd unit; `scripts/kiosk/` rename internals.
- Client: brand strings, "Connecting to SignBoard…" → "Connecting to ExhibitOS…",
  Wharfside navy/gold CSS vars → museum-neutral theme (InfoAge house style for cards).
- Repo-wide: `signboard` → `exhibitos` identifier sweep (config keys, env prefixes).

### 9.4 Modules — built and to-build

**Built (the wiki-ingest content path):**
- `server/services/wiki_ingest.py` — DokuWiki parser + idempotent upsert + counts.
- `server/models/exhibit.py` — the `Exhibit` read-cache model.
- `server/api/exhibits.py` — public `GET /api/exhibits` (sort_order) + `GET /api/exhibits/{slug}`;
  authed `POST /api/exhibits/ingest`.
- `scripts/ingest_wiki.py` — the `python -m scripts.ingest_wiki` CLI.

**To build:**
- `server/services/print_service.py` — Playwright card export.
- `server/services/dokuwiki_api.py` (later) — live DokuWiki API reader feeding the same parser.
- `server/api/display.py` — `GET /api/display/<room-slug>` (reads read-cache + assignment).
- `server/api/assignments.py` — admin assignment CRUD.
- `server/api/print.py` — `POST /api/print/card/<slug>`.
- `server/models/display_assignment.py`, `display_device.py`, `overlay.py`.
- `client/src/display/cards/InfoAgeHouseCard.tsx`, `VideoDisplay.tsx`,
  `TouchInteractive.tsx`, `RoomDisplay.tsx`.

---

## 10. Deployment Topology

### 10.1 Mini PC (the one server)

Docker Compose with a **single** ExhibitOS service. The content system of record — the docent
wiki — is **external** (the museum already runs it); there is no CMS or extra database to host:

```yaml
services:
  exhibitos:       # Ingest + renderers + fleet (refactored SignBoard)
    build: .
    ports: ["8100:8100"]
    environment:
      WIKI_EXPORT_PATH: /data/wiki-export/the_artifacts.txt   # v1 ingest source (file)
      # (later) DOKUWIKI_API_URL / DOKUWIKI_API_TOKEN for live-API ingest
      DATABASE_URL: sqlite:////data/exhibitos.db
      MEDIA_DIR: /data/media
      JWT_SECRET_KEY, DEFAULT_ADMIN_PASSWORD
    volumes:
      - exhibitos_data:/data                   # SQLite (Exhibit read-cache) + media + wiki export
    # Playwright Chromium bundled in this image (print, server-side only)
volumes: [exhibitos_data]
```

- **The docent wiki is external** — ExhibitOS reads it (a mounted/synced export file in v1, the
  live DokuWiki API later) and never hosts it. The `Exhibit` read-cache + deliverable media live
  in `exhibitos_data:/data` so displays never re-parse the wiki.
- **ExhibitOS Dockerfile** gains a Playwright Chromium install layer (D7). Note the current
  `512M` memory limit (compose) must rise — Chromium for PDF export needs headroom; recommend
  **2 GB** for the exhibitos service. A typical mini PC (8–16 GB) handles it with room to spare —
  and with no CMS/Postgres there's far less to allocate than the earlier multi-service design.
- Reverse proxy (Caddy/nginx, optional) terminates TLS and routes `/` → exhibitos for a clean
  museum-branded URL.

### 10.2 Kiosks

| Class | Device | Platform / transport | Typical profile (orientation · resolution · DPR · size@dist) | Form layout | Tier-2 cache |
|---|---|---|---|---|---|
| passive card/video | Pi Zero 2 W + monitor (~$15) | `chromium-kiosk` / WS | landscape · 1920×1080 · 1.0 · 43″@8ft | card: landscape canvas; video: responsive | Service Worker + SD |
| passive card/video | Onn FHD stick (~$20) + any TV | `fully-kiosk` / REST :2323 | landscape · 1920×1080 · 1.0 · 55″@10ft | card: landscape canvas; video: responsive | Fully Kiosk webview cache + SW |
| passive (large/lobby) | Google TV / 4K panel | `fully-kiosk` / REST :2323 | landscape · **3840×2160 · DPR 2** · 75″@15ft (high text_scale) | card: landscape canvas, scaled; video: responsive 4K | same |
| passive (corridor sign) | **portrait-mounted** panel + Pi/stick | either | **portrait · 1080×1920** · 49″@6ft | **card: portrait canvas** (distinct comp.) | per platform |
| touchscreen | Pi/legacy PC + touch panel | `chromium-kiosk` / WS | landscape **or portrait** · 1080p–1280×800 · varies | interactive: responsive fluid grid | Service Worker + disk |
| passive (repurposed) | legacy museum PC + monitor | `chromium-kiosk` (x86) / WS | landscape · varies (odd aspect → pillarbox) | card: landscape canvas, letterboxed | Service Worker + disk |

Each kiosk points at `http://<minipc>:8100/display/<room-slug>?device_id=<id>` (the dashboard
bakes the `device_id` into the assigned URL so the served page can report its profile and the
display API can resolve the device; or via reverse proxy / Tailscale). Pi/legacy PC provisioned via refactored `scripts/kiosk/`; Fully Kiosk devices
via the 10-minute manual setup (`signboard-onn-fhd-kiosk-setup.md`, renamed).

### 10.3 Network assumptions

- All devices + mini PC on **one museum LAN** (InfoAge gallery network). Fully Kiosk REST
  (:2323) is **LAN-only**, never exposed publicly.
- Static IP/DHCP reservation per Fully Kiosk device (REST needs a stable IP).
- **Tailscale** (optional) for off-site admin: the mini PC is a subnet router/exit node;
  admin reaches the dashboard + (proxied) Fully Kiosk REST over the tailnet. Public QR
  targets resolve over the open internet (wiki/YouTube) — independent of LAN.
- No inbound public exposure of the dashboard required for v1 (admin is on-LAN or Tailscale).
  The only public surface is the QR deep-content host (external).

---

## 11. Non-Functional Requirements

### 11.1 Offline resilience (the headline NFR)

- **Wiki unreachable:** the Tier-1 `Exhibit` read-cache serves all displays; re-ingest simply
  resumes when the wiki is back. No display interruption (narrative edits are infrequent).
- **Mini PC / LAN down:** Tier-2 Service Worker / Fully Kiosk cache keeps each kiosk on
  its last-known-good render; staleness indicator shown.
- **Never demo data** (PRD §8.3, feedback `no-demo-fallback`): on genuinely-missing
  content, every renderer shows a clear error state, not placeholder content.

### 11.2 Security

| Surface | Posture |
|---|---|
| **Public QR / deep content** | Read-only, external (wiki/YouTube). No ExhibitOS attack surface. |
| **ExhibitOS → wiki ingest** | One-way **read-only** pull (export file in v1; authenticated read-only API later); ExhibitOS never writes to the wiki. A wiki read credential exposes only docent-authored content. |
| **Wiki authoring** | The docent wiki's own accounts/roles + revision history; outside ExhibitOS's trust boundary. |
| **ExhibitOS dashboard** | Existing JWT admin auth; on-LAN/tailnet; not publicly exposed in v1. Controls display config + re-ingest only. |
| **Fleet — `chromium-kiosk` WS** | `DEVICE_AGENT_TOKEN` bearer on WS handshake; `update-scripts` restricted to a pinned repo/branch (no arbitrary command exec). The `display_profile` carried on the handshake/`/api/devices/{id}/profile` is non-sensitive screen geometry. |
| **Fleet — `fully-kiosk` REST** | Per-device password (masked in ExhibitOS settings); LAN-only :2323; never proxied publicly. The served-page profile probe (§6a.4) POSTs only screen geometry, LAN-side. |
| **Display profile probe** | `POST /api/devices/{id}/profile` accepts only the geometry payload (resolution/orientation/DPR); device resolved by baked `device_id` or source IP; LAN/tailnet only; no auth required (same posture as unauthenticated display reads) but writes only non-sensitive profile fields and never the manual size/distance. |
| **Display / exhibit routes** | Unauthenticated read (kiosks need no login); serve the ingested read-cache. `POST /api/exhibits/ingest` is the only authed exhibit endpoint. |
| **Kiosk navigation** | Locked to the ExhibitOS origin via Fully Kiosk URL allowlist + Chromium `URLAllowlist`/`URLBlocklist` policy; context menus disabled; no clickable off-origin links; kiosk video is self-hosted HTML5 (no YouTube iframe). Prevents visitors escaping into the open web (issue #37). |
| **Secrets** | Wiki read credential (live-API phase), Fully Kiosk passwords, JWT key in env/`.env` + masked settings; per `credentials-apple-passwords` feedback, avoid plaintext credential files where a manager exists. |

### 11.3 Performance on cheap hardware

- **Pi Zero 2 W** renders a single static card / looping video — well within its means
  (SignBoard already proves this at Wharfside). Service Worker keeps it responsive offline.
- **Displays read from SQLite + local media** (Tier 1) — no per-request network round trip,
  no re-parsing the wiki. The exhibit list/detail is a single indexed query.
- **Playwright print is server-side only** and on-demand (not on render path) — its cost
  never touches kiosks.
- **Ingest is idempotent and cheap** — `content_hash` skips unchanged exhibits; only changed
  ones write. Re-ingest runs on demand, off the render path.

### 11.4 Backup

- **The wiki = the only thing that must be backed up for content** (it is the SoR). The museum
  already backs up its wiki; ExhibitOS adds no content backup burden.
- ExhibitOS SQLite (`exhibitos_data`) is **largely regenerable** — the `Exhibit` read-cache and
  ingested narrative rebuild from the wiki on the next ingest. The unique state worth backing
  up nightly is the **ExhibitOS-owned display fields** (hero/video/deep-link/location) plus
  `display_assignment` + `display_device` (small; faster recovery than re-attaching assets and
  re-provisioning the fleet mapping) and the media binaries in `/data/media`.
- Recovery drill: restore `exhibitos_data` → bring up ExhibitOS → re-ingest from the wiki →
  fleet reconnects. RPO ≤ 24h (nightly), RTO ≈ minutes (Compose up + ingest).

---

## 12. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **DokuWiki export/API format drift** breaks the parser | Med | Med | The parser is isolated (`parse_dokuwiki()`), covered by the `the_artifacts` dump as test data; the file-ingest phase decouples parsing from a live connection; pin to the museum's wiki version and re-test on upgrades. **Flagged to Nick.** |
| R2 | **Playwright/Chromium bloat** on the mini PC image + memory | Med | Med | Print is server-side, on-demand, isolated; raise exhibitos memory limit to 2 GB (§10.1); consider a separate `playwright` sidecar container if the main image gets unwieldy. |
| R3 | **Stale displays between re-ingests** | Low | Low | v1 re-ingest is on-demand (button/CLI); the "last ingested HH:MM" indicator surfaces staleness; the live-API phase moves to a schedule. Narrative edits are infrequent. |
| R4 | **Fully Kiosk auto-update breaks REST/kiosk mode** (noted in google-tv-spec) | Low | Med | Disable Play Store auto-update per device; validate on one device before fleet rollout. |
| R5 | **Re-ingest clobbers ExhibitOS-owned display fields** | Low | High | The built upsert **never** writes `hero_image`/`video_url`/`deep_content_url`/`location` on re-ingest; covered by the idempotency design (§5.2) and worth a regression test on every parser change. |
| R6 | **Wiki page → exhibit mapping ambiguity** (which pages are exhibits; duplicate titles) | Med | Med | The parser keys on level-5 headings and derives stable slugs with `-2`/`-3` suffixes for duplicate titles; confirm the ingested namespace with the docents (OPEN-QUESTIONS §4). |
| R7 | **Card print drift from on-screen** (the thing Playwright is meant to prevent) — regressions via diverging print CSS | Low | Med | Single shared component; print differences only in a print stylesheet, not a fork; visual review vs InfoAge's 9 signs is an explicit acceptance gate (PRD §6.1). |
| R8 | **`related_exhibits` rendering loops** (3280→Onyx→3280) on touch interactive | Low | Low | Render "see also" as explicit navigation (not auto-expand); depth-1 traversal per tap; no recursive embed. |
| R9 | **Service Worker stale-bundle on iOS-style caches** (cf. feedback `ios-pwa-double-relaunch`) | Low | Low | `vite-plugin-pwa` autoUpdate + a visible app version; document the "two force-closes / reload" recovery in the runbook; Fleet "Reload" handles it remotely. |
| R10 | **Volunteer can't self-serve** (fails PRD §8 headline test) | Med | High | Authoring in the wiki the docents already use + the clean dashboard (assign-to-rooms) + the required volunteer runbook (PRD §8.2); validate with a real InfoAge volunteer before "done." |
| R11 | **Media store disk growth** on the mini PC (self-hosted videos) | Med | Med | Kiosk video is self-hosted (no YouTube on kiosks, 2026-06-01 policy), so video binaries live on disk: stream downloads to disk (no in-memory buffering), serve with HTTP range, store only what's referenced by an exhibit's `video_url`, prune orphans, and monitor disk. |

---

## 13. v1 Build Order (for dev-planning handoff)

0. **Wiki-ingest content path — BUILT.** The `Exhibit` model, `wiki_ingest.py` (parser +
   idempotent upsert), `api/exhibits.py` (public list/detail + authed ingest), and the
   `scripts.ingest_wiki` CLI exist and parse the `the_artifacts` dump.
1. **Refactor & rename** (§9): strip Wharfside modules, rename SignBoard→ExhibitOS,
   replace Page/Channel with `display_assignment`/`display_device` (the `Exhibit` read-cache
   already replaces the SignBoard content columns).
2. **Display API + RoomDisplay** routing reading the `Exhibit` read-cache + assignments;
   **Card renderer** (`InfoAgeHouseCard`) in **both landscape and portrait** canvases;
   **Display Profile** auto-detect handshake + manual size/distance, and the **text-scale
   system** (§6a) applied across all forms.
3. **Playwright print** (`print_service.py`) — prove screen/print parity on the 3280 card.
4. **Video + Touch interactive** renderers (touch gate).
5. **Fleet**: rename agent → `exhibit-agent`, `/ws/device-agent`, Fully Kiosk bridge,
   Fleet tab.
6. **Dashboard**: display assets (hero/video/deep-link), Re-ingest, Exhibits tab, assignment.
7. **Author the Concurrent 3280** in the wiki (incl. the Onyx 10000 `related_exhibits` link),
   ingest it, and render on 1–2 real InfoAge displays.
8. **Live DokuWiki API ingest** (Phase 2) through the same parser, on a schedule.
9. **Handoff package** (§8): volunteer runbook + admin setup guide; validate with a real
   volunteer.

---

## 14. Open Items to Relay to Nick (orchestrator → Nick)

1. **Wiki read access (PRD §9b #7).** v1 ingests a DokuWiki **export file**; the live-API phase
   needs the wiki's API enabled and a read-only docent account. Confirm the API is available and
   agree on the export/API access method with the docents.
2. **Which wiki pages are exhibits.** Confirm the namespace/page set ExhibitOS should ingest, and
   the convention that marks a page as an exhibit (the parser keys on level-5 headings today).
3. **Public deep-content target (PRD §9b #8).** The docents' wiki is login-gated; the QR needs a
   *public* page — ExhibitOS hosts it, or VCF opens a public wiki section. Confirm preference.
4. **Mini PC memory headroom (R2).** A single ExhibitOS service + bundled Chromium wants ~2 GB.
   Confirm the target mini PC has the RAM (8 GB+ recommended — comfortably more than enough now
   that there's no CMS/Postgres).
5. **Kiosk video = self-hosted HTML5 (RESOLVED 2026-06-01).** Kiosks never embed YouTube
   (escape risk on public/touch screens); they play self-hosted `<video>` from the mirror.
   YouTube is reserved for the phone/QR deep-content page. Media mirror now holds video
   binaries (R11), and a browser-level URL-allowlist lockdown (issue #37) is the backstop.
6. **Full portrait support + Display Profile in v1 (DECIDED 2026-06-01).** The interpretive
   card now ships **two designed canvases** (landscape + portrait); video/touch are responsive.
   Each display carries a **Display Profile** (resolution/orientation/DPR auto-detected; physical
   size + viewing distance entered manually) that drives orientation layout and a physical
   text-scale (§6a). This **supersedes** the UX-SPEC §8.2 "portrait is Phase 2" note and the
   earlier card decision "fixed 1920×1080 canvas." Two human inputs to relay: (a) confirm the
   **portrait card composition** matches InfoAge house style on a real portrait sign at first
   print proof; (b) confirm the **text-scale baseline** (24″@5ft) and the manual
   `physical_size_in`/`viewing_distance_ft` capture step are acceptable in the volunteer/admin
   workflow (admin sets size+distance once per display at provisioning).

---

## 15. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-05-31 | Software Architecture (AI-assisted) | Initial architecture. Device-location (ExhibitOS-only, assign-to-rooms), form precedence (assignment>default, class-gated). Two-tier cache design, fleet protocol, render targets, SignBoard refactor map, deployment topology, NFRs, risks. (The content-source design here named a self-hosted CMS; reversed in 0.3 — see ADR-0001.) |
| 0.2 | 2026-06-01 | Software Architecture (AI-assisted) | **Display Profile & Render Path (new §6a, D12).** Added per-display profile (platform/class/resolution/orientation/DPR/physical-size/viewing-distance) to `display_device`; render path = transport × orientation layout × physical text-scale × class-allowed forms. Full **portrait support in v1** (distinct portrait card canvas; video/touch responsive). Physical-size+distance **text-scale** rule preserving ADA minimums. Auto-detect handshake for both transports (WS agent frame + served-page probe for Fully Kiosk). Renamed platforms to `chromium-kiosk`/`fully-kiosk`. Updated §6.1/§6.2/§7/§10.2/§11.2/§13/§14. |
| 0.3 | 2026-06-05 | Software Architecture (AI-assisted) | **Content architecture refactor (ADR-0001).** Reworked the design around the **docent wiki as system of record + ExhibitOS wiki-ingest** to match the built code: replaced the CMS framing (§1–§3), the multi-collection content model (§4) with the single `Exhibit` read-cache model (`models/exhibit.py`), and the webhook/poll sync (§5) with idempotent `content_hash` upsert + on-demand re-ingest (`wiki_ingest.py`, `api/exhibits.py`, `scripts.ingest_wiki`). Updated render targets (§7), refactor map (§9), single-service deployment (§10), security/backup/perf (§11), risks (§12), build order (§13), and open items (§14). The previously-evaluated CMS survives only as the explored option (see ADR-0001 and the explored-option primer in `docs/`). |
