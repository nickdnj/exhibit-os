# Technical Architecture: ExhibitOS

**Version:** 0.1
**Last Updated:** 2026-05-31
**Author:** Software Architecture (AI-assisted), for Nick DeMarco
**Status:** Draft — for review
**PRD Reference:** [`docs/PRD.md`](./PRD.md) v0.2
**Repo:** `github.com/nickdnj/exhibit-os` · local `~/Workspaces/exhibit-os`

---

## 0. How to read this document

This architecture is **prescriptive enough to scaffold from.** The Directus content
model (§4) is precise to the field/type/relation level. The refactor map (§9) names
real files in the seeded repo. The deployment topology (§10) is concrete Docker Compose.

Everything here respects the **locked decisions** in PRD §9a (Directus as system of
record, Playwright print, configurable QR, two-tier cache, one-deployment-per-museum)
and **resolves** the three still-open items in PRD §9b with opinionated recommendations
(see §3 and the relevant sections). It does **not** re-open any locked decision.

---

## 1. Architecture Overview

ExhibitOS is a **two-process system** behind one mini PC, with a fleet of dumb web
clients hanging off it. The defining principle is a hard separation between **content**
(owned by Directus) and **presentation + fleet control** (owned by ExhibitOS):

- **Directus** is the **system of record (SoR)** for ALL content — assets, rooms,
  people, media, relations, draft/published state, revision history, the media library,
  and the authoring UI. Volunteers only ever touch Directus to create or edit content.
- **ExhibitOS** (the refactored SignBoard core: FastAPI + React + SQLite + WebSocket)
  is a **thin renderer + sync + fleet layer.** It consumes the Directus API, mirrors
  content into a local cache, renders content by device class, exports printable cards
  via Playwright, and controls the physical fleet. It stores **no content** — only
  display-assignment config and a read-cache.

Displays **never talk to Directus directly.** They talk only to ExhibitOS, which serves
from its local mirror. This is the first tier of the two-tier cache and the reason a
Directus outage does not blank the gallery.

### 1.1 Component diagram (text)

```
┌───────────────────────────────────────────────────────────────────────────┐
│ AUTHORING (Curator "Doug")                                                  │
│   Directus Admin UI ──writes──▶ DIRECTUS  (System of Record, Postgres)      │
│   roles · drafts · review/approve · media library · revision history        │
│   collections: asset · room · person · media_item · setting                 │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │  (1) publish webhook  ─────────────┐
                           │  REST/GraphQL (read-only token)     │ HTTP POST on
                           ▼                                     │ items.*.create/
┌───────────────────────────────────────────────────────────────│──update/delete
│ EXHIBITOS SERVER  (mini PC, Docker)  — SYNC · RENDER · FLEET    │            │
│                                                                 ▼            │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ SYNC SERVICE  (directus_sync.py)                                       │ │
│   │   webhook-triggered + 5-min poll safety net                            │ │
│   │   pulls changed items → writes LOCAL CACHE (SQLite content_cache)      │ │
│   │   downloads referenced media files → MEDIA MIRROR (/data/media)        │ │
│   └───────────────────────┬──────────────────────────────────────────────┘ │
│                           ▼                                                   │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ LOCAL CACHE (SQLite)            DISPLAY-ASSIGNMENT CONFIG (SQLite)       │ │
│   │  content_cache (mirror of      display_device · display_assignment      │ │
│   │  Directus items, read-only)    overlay · schedule · setting             │ │
│   │  media files on disk           (repurposed SignBoard Page/Channel)      │ │
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

**Directus is the only place content is created or edited; ExhibitOS is the only place
displays are configured and controlled; they communicate over a one-way, read-only,
cached pull (with a publish webhook to make it near-real-time).**

---

## 2. Key Architectural Decisions (summary table)

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Content system of record | **Directus** (self-hosted Docker) | PRD-locked. Don't rebuild a CMS. |
| D2 | Directus database | **Postgres** (not SQLite) | Directus officially supports Postgres for prod; revision history + concurrent authoring need a real RDBMS. ExhibitOS keeps SQLite. |
| D3 | ExhibitOS↔Directus auth | **Static read-only Directus token** in a `read-published` role | PRD §9b — recommend for v1. Simple, no rotation infra. Stored in `.env` / Settings. (§3.1) |
| D4 | `display_device` location | **ExhibitOS only; authors assign to *rooms*** | PRD §9b lean confirmed. Devices are physical/fleet state, not content. (§3.2) |
| D5 | Form precedence | **assignment form > device `default_form`**, gated by `device_class` | PRD §9b resolved. (§3.3) |
| D6 | Cache invalidation | **Directus webhook (push) + 5-min poll (safety net)** | Near-real-time without polling storm; poll guarantees eventual consistency if a webhook is missed. (§5) |
| D7 | Card print pipeline | **Playwright headless Chromium, server-side** | PRD-locked. One HTML/CSS template → pixel-identical screen + print. |
| D8 | QR resolution | **`{qr_base_url}/{slug}`** + per-asset absolute override | PRD-locked. |
| D9 | Fleet protocol | **Two protocols, bridged not unified** (Pi=WS push, FullyKiosk=REST pull) | PRD-locked; inherited from SignBoard fleet specs verbatim. |
| D10 | Tenancy | **One deployment per museum; no museum-scoping field** | PRD-locked. |
| D11 | Tier-2 kiosk cache | **Service Worker (Pi/legacy PC) + Chromium HTTP cache** | Real local storage on each kiosk; survives server/network outage. (§5.3) |

### 2.1 Technology stack

| Layer | Technology |
|---|---|
| Content SoR | Directus (latest stable), Postgres 16 |
| ExhibitOS API / sync / fleet | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0, httpx |
| Card print | Playwright (Python) + bundled Chromium |
| Dashboard + display clients | React 19, React Router 7, Tailwind 4, Vite 8 |
| ExhibitOS store | SQLite (assignment config + content cache) |
| Media mirror | Local filesystem volume on mini PC |
| Fleet | WebSocket (Pi/legacy PC agent) + Fully Kiosk REST :2323 (TV/stick) |
| Containerization | Docker Compose on the mini PC |
| QR | `qrcode[pil]` (already stubbed in requirements.txt) |

---

## 3. Resolved Open Questions (PRD §9b)

### 3.1 Auth between ExhibitOS and Directus → static read-only scoped token (v1)

**Decision.** ExhibitOS authenticates to Directus with a **single static API token**
belonging to a dedicated Directus user (`exhibitos-sync`) assigned a custom role
**`read-published`**. That role has:

- **Read** on `asset`, `room`, `person`, `media_item`, `setting`, `directus_files`
  — **filtered to `status = published`** (item-level permission filter) for collections
  that have a status; full read on `media_item`/`person`/`directus_files` since they are
  referenced by published assets.
- **No** create/update/delete anywhere. No access to `directus_users`, roles, or admin.

**Token storage & rotation posture.**
- v1: token lives in the ExhibitOS container env (`DIRECTUS_TOKEN`) sourced from `.env`,
  and is also surfaced (masked) in the ExhibitOS `setting` store so an admin can rotate
  it from the dashboard without editing files. On change, the sync service reloads it.
- Rotation procedure (documented in the admin guide): create a new static token in
  Directus for `exhibitos-sync`, paste into ExhibitOS Settings, save, delete the old
  token in Directus. No service restart required.
- We deliberately **do not** build OAuth/refresh-token rotation in v1 — the token is
  read-only, scoped to published content, and never leaves the LAN/Tailscale boundary.
  A leaked token exposes only already-public museum content. Upgrade path (Phase 2): a
  short-lived service-account token with a refresh loop, if a museum's threat model
  demands it.

**Admin auth stays separate from Directus auth (two logins) for v1.** The ExhibitOS
dashboard keeps its existing JWT admin auth (the SignBoard `admin_user` table). Directus
has its own user accounts for authors/reviewers. Reasons: (a) the two surfaces have
different audiences — content authors vs. the single infra admin; (b) SSO (e.g. Directus
as an OIDC provider for ExhibitOS) is real work for marginal v1 benefit. **Documented
future improvement:** unify via Directus-as-IdP so a volunteer has one login. Flagged to
Nick in the handoff notes.

### 3.2 Where `display_device` lives → ExhibitOS only; authors assign to rooms

**Decision.** `display_device` is **removed from the Directus content model.** Devices
are physical fleet state (online/offline, IP, heartbeat, platform, class) — that is not
content and does not belong in the SoR. It lives solely in the ExhibitOS SQLite
`display_device` table (the renamed/extended SignBoard `kiosks` table).

**Consequence for authoring.** Authors **assign content to rooms, not to devices.**
A `room` is a first-class Directus collection (it *is* content — it has a name,
description, hours). The ExhibitOS dashboard maps rooms → physical devices. So the
author's mental model is "this exhibit shows in the Main Gallery"; the admin's model is
"the Main Gallery has a passive card display (Pi) and a touchscreen (Onn)." Each device
is bound to exactly one room and renders that room's feed in the device's form.

**Why this is right:**
- Keeps the SoR purely about content; keeps fleet churn (a Pi dies, gets reflashed, gets
  a new IP) out of the content database and its revision history.
- Matches the personas: Doug thinks in rooms and exhibits; Nick thinks in devices.
- Removes the §5.5 "mirrored collection" ambiguity entirely — there is no mirror to keep
  in sync, no split-brain over device truth.

The `room.slug` remains the feed key used in the display URL `/display/<room-slug>`,
preserving SignBoard's subscribe-by-slug model.

### 3.3 Form precedence: per-asset vs per-assignment → assignment wins, gated by class

Three things influence what renders on a screen: `asset.card_template` (a *style* hint,
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
3. **`card_template` is orthogonal** — it selects *which* card style/print template
   (`infoage-house`, etc.) to use *when* the form is `card`. It never selects a form.

So: **`device_class` (gate) → assignment form (if present and allowed) → `default_form`
(fallback) → `card_template` (style, only when form=card).** This lets a curator "force a
card onto a video-default screen for a day" (PRD §9b example) simply by making an
assignment with `form=card`; it does not let them force interactive onto a passive panel.

---

## 4. Directus Content Model (scaffold-precise)

All collections live in **Directus** (Postgres-backed). Every collection has the implicit
Directus system fields: `id` (uuid), `date_created`, `date_updated`, `user_created`,
`user_updated`. Collections with authoring lifecycle add a `status` field. Field types
below are **Directus field types**; relation rows note the junction collection Directus
auto-creates.

> **Single-museum (D10):** no `museum` scoping field on any collection.

### 4.1 `asset` — Asset / Exhibit (central record)

| Field | Directus type | Constraints / notes |
|---|---|---|
| `id` | uuid (PK) | system |
| `status` | string (dropdown) | `draft` / `in_review` / `published` / `archived`; drives publish gate + approval |
| `title` | string | **required** — "The Concurrent 3280" |
| `subtitle` | string | "The last great pre-RISC scalar minicomputer" |
| `slug` | string | **required, unique** — `concurrent-3280`; used in QR `{qr_base_url}/{slug}` |
| `hero_image` | M2O → `media_item` | primary photo for card + interactive |
| `interpretive_body` | text (markdown / WYSIWYG) | main narrative |
| `bullet_facts` | JSON | array of strings (the sign "Bullets") |
| `backstory` | text (markdown) | "The Backstory:" sub-section |
| `closer` | text | closer / easter-egg strip line |
| `qr_target_url` | string | **optional absolute-URL override**; when empty, QR uses `{qr_base_url}/{slug}` |
| `deep_content_url` | string | canonical deep page (wiki entry) |
| `youtube_url` | string | YouTube link for the **phone/QR deep-content page only** — NOT played on kiosks (kiosk video is self-hosted; see §7.2 / 2026-06-01 policy) |
| `card_template` | string (dropdown) | `infoage-house` (default) / future styles — **style, not form** |
| `featured` | boolean | dashboard sorting |
| `sort` | integer | manual ordering within a room |

**Relations:**

| Relation | Cardinality | Target | Junction / FK | Notes |
|---|---|---|---|---|
| `room` | M2O | `room` | `asset.room` FK | physical location |
| `people` | M2M | `person` | `asset_person` junction | inventors/architects; junction has `sort` for ordering (people[0] = primary portrait on card) |
| `media` | M2M | `media_item` | `asset_media_item` junction | gallery; junction has `sort` for ordered gallery |
| `related_assets` | **M2M self-referential** | `asset` | `asset_related_asset` junction (`asset_id`, `related_asset_id`, `relationship_note`) | the **3280 ↔ Onyx 10000** cross-reference; `relationship_note` string ("same architect, 30 ft away") |

> **Self-referential relation, concretely.** Create an M2M from `asset` to `asset`. The
> junction collection `asset_related_asset` has columns `asset_id` (uuid FK→asset),
> `related_asset_id` (uuid FK→asset), `relationship_note` (string), `sort` (integer). The
> relation is **directional** as stored; ExhibitOS renders it as "see also" from the
> owning asset. For a reciprocal link (Onyx also points back to 3280) the author creates
> the inverse junction row — we do **not** auto-mirror, to keep author intent explicit.

### 4.2 `room` — Room / Location

| Field | Directus type | Notes |
|---|---|---|
| `id` | uuid (PK) | |
| `name` | string | **required** — "VCF Main Gallery" |
| `slug` | string | **required, unique** — feed id: `/display/<slug>` |
| `description` | text | optional room intro |
| `operating_hours` | JSON | per-day `{open, close}` → drives scheduled screen on/off |
| `floor_map_ref` | string | optional location reference |

**Relations:** `assets` — O2M ← `asset.room`. (No `devices` relation — devices live in
ExhibitOS per D4. ExhibitOS joins room→devices by `room.slug`.)

### 4.3 `person` — Person

| Field | Directus type | Notes |
|---|---|---|
| `id` | uuid (PK) | |
| `name` | string | **required** — "Ken Yeager" |
| `credentials` | string | "MIT '72" |
| `role_label` | string | "architect of the 3280" |
| `bio` | text (markdown) | full bio for interactive/deep content |
| `portrait` | M2O → `media_item` | headshot |
| `lifespan` | string | "1949–2017" |

**Relations:** `assets` — M2M ← `asset.people` (via `asset_person`).

### 4.4 `media_item` — MediaItem (museum-grade attribution)

| Field | Directus type | Notes |
|---|---|---|
| `id` | uuid (PK) | |
| `status` | string (dropdown) | `draft` / `published`; published requires caption+source+credit |
| `file` | M2O → `directus_files` | the upload (image or video) |
| `media_type` | string (dropdown) | `image` / `video` / `external_video` |
| `external_url` | string | for `external_video` (YouTube/Vimeo) |
| `caption` | text | **required when published** |
| `source` | string | **required when published** — provenance |
| `credit` | string | **required when published** — attribution |
| `alt_text` | string | accessibility |

Published-requires-attribution is enforced by a **Directus Flow** (validation on
status→published transition) so a volunteer can't publish an uncredited photo.

**Relations:** referenced by `asset.hero_image`, `asset.media`, `person.portrait`.

### 4.5 `setting` — Platform settings (small singleton-ish collection)

Holds platform config authors might legitimately touch as content (vs. infra config in
ExhibitOS). Minimal in v1:

| Field | Type | Notes |
|---|---|---|
| `key` | string (unique) | e.g. `qr_base_url`, `museum_name` |
| `value` | string | |

> **Where does `qr_base_url` live?** It is *content-adjacent* and we put the canonical
> copy in Directus `setting` so authors can change it without admin. ExhibitOS caches it
> like any other content. (ExhibitOS-internal infra settings — Directus URL, token, Fully
> Kiosk passwords — stay in the ExhibitOS `setting` SQLite table, never Directus.)

### 4.6 Relations summary

```
asset ──M2O──▶ room                         (asset.room)
asset ──M2M──▶ person       via asset_person            (sort)
asset ──M2M──▶ media_item   via asset_media_item        (sort)   [hero_image is a separate M2O]
asset ──M2M──▶ asset        via asset_related_asset      (relationship_note, sort)  [self-ref]
person ─M2O──▶ media_item                   (person.portrait)
media_item ─M2O▶ directus_files             (media_item.file)
room  ──O2M──▶ asset                        (inverse of asset.room)
# display_device is NOT in Directus (lives in ExhibitOS, see §4.x / §6)
```

### 4.7 Roles & approval workflow (Directus)

| Role | Permissions | Persona |
|---|---|---|
| **Author** | create/read/update own `asset`/`media_item`/`person`; can set status to `draft`/`in_review`; **cannot** set `published` | Doug (volunteer) |
| **Reviewer** | all Author perms + can transition `in_review` → `published`; read all | senior volunteer |
| **Admin** | full | Nick / future admin |
| **`read-published`** (API) | read-only, `status=published` filtered; used by the ExhibitOS static token | (no human) |

Workflow: Author creates Draft → submits (`in_review`) → Reviewer publishes
(`published`). Directus revision history is retained automatically. This satisfies PRD
§8.2 "roles + review workflow."

---

## 5. Data Flow, Sync & Two-Tier Cache

### 5.1 Authoring → publish → render (end to end)

```
1. Author edits asset in Directus, sets status=in_review.
2. Reviewer sets status=published.
3. Directus fires a Flow → webhook  POST {EXHIBITOS}/api/sync/webhook
   with {collection, event: items.update, keys:[id], status:"published"}.
4. ExhibitOS sync service:
     a. Validates webhook (shared HMAC secret header).
     b. Pulls the changed item(s) + their relations from Directus REST
        (read-only token), e.g. GET /items/asset/<id>?fields=*,people.*,
        media.*,related_assets.*,hero_image.*,room.*
     c. Upserts into SQLite content_cache (one row per item, JSON blob +
        denormalized index columns: slug, status, room_slug, updated_at).
     d. For each referenced directus_files asset, downloads the binary to
        /data/media/<file_id>.<ext> if missing or changed (ETag/checksum).
5. ExhibitOS notifies affected displays via existing WebSocket:
     ws_manager.notify_content_changed(room_slug)  (renamed notify_page_update)
6. Display clients receive {type:"content_changed"} → refetch
   GET /api/display/<room-slug> (served from content_cache + assignment config).
7. Kiosk renders; Service Worker updates its tier-2 cache for offline use.
```

### 5.2 Cache invalidation: webhook (push) + poll (safety net) — D6

- **Primary: Directus webhook (push).** A Directus Flow on
  `items.create`/`items.update`/`items.delete` for `asset`, `room`, `person`,
  `media_item`, `setting` POSTs to `/api/sync/webhook`. This makes the server mirror
  near-real-time (sub-second to a few seconds). The webhook carries the collection +
  keys; ExhibitOS pulls fresh (we do **not** trust webhook payload as content — we
  re-fetch via the read-only token to get the full relational graph and respect the
  published filter).
- **Safety net: 5-minute poll.** A background task (`directus_sync.poll_loop`) queries
  Directus for items with `date_updated` since the last successful sync watermark and
  reconciles. This covers missed webhooks (server was down, webhook lost) and guarantees
  **eventual consistency**. Poll is cheap (filter by `date_updated`, fetch only deltas).
- **Acceptable staleness window:** **≤ 5 minutes worst case** (a fully missed webhook
  reconciled by the next poll); **typically < 5 seconds** (webhook path). For a museum
  exhibit this is comfortably within "fix a typo, it updates on next refresh" (PRD §3.1).
- **Full resync** on ExhibitOS startup and via a dashboard "Resync from Directus" button
  (admin) — walks all published items, rebuilds `content_cache`, prunes orphans.

### 5.3 Two-tier cache, concretely

**Tier 1 — ExhibitOS server-side mirror (the mini PC).** This is the authoritative copy
*for displays*. It comprises:

- `content_cache` SQLite table: every published Directus item, stored as `{id,
  collection, slug, status, room_slug, data_json, updated_at}`. Renderers read from here,
  **never** from Directus live.
- `/data/media` filesystem mirror: every referenced image/video binary, named by Directus
  file id. Served by ExhibitOS at `/media/<file_id>` (replaces SignBoard's `/uploads`).
- Result: **if Directus is down, displays keep working** off the last good mirror. The
  dashboard shows a "Directus unreachable — serving cached content (last sync: HH:MM)"
  banner. **No demo/placeholder content, ever** (PRD §8.3, feedback `no-demo-fallback`):
  if the mirror has no content for a room, the display shows a clear error state.

**Tier 2 — kiosk-local cache (each Pi / legacy PC / TV).** Each kiosk degrades gracefully
through a *network or server* outage:

- **Pi / legacy PC (Chromium):** the React display app ships a **Service Worker**
  (via `vite-plugin-pwa`) with a cache-first strategy for `/api/display/<room>` and
  `/media/*`. On load it caches the room feed JSON + media. If the mini PC or LAN drops,
  the Service Worker serves the last-known-good render from local disk. On reconnect it
  revalidates (stale-while-revalidate). Pi has SD-card storage; legacy PCs have disk —
  both have "real local storage" per PRD §9a.3(b).
- **Onn stick / Google TV (Fully Kiosk):** relies on Fully Kiosk's built-in webview HTTP
  cache plus the same Service Worker (Fully Kiosk runs Chromium and supports SWs). Fully
  Kiosk's "reload on network reconnect" handles re-sync.
- **Staleness signal:** the display footer shows a subtle "offline — last updated HH:MM"
  indicator when the Service Worker is serving cached content, so staff can tell a frozen
  screen from a genuinely-cached one.

> **Three layers of resilience.** Directus down → Tier 1 serves. Mini PC/LAN down →
> Tier 2 serves. Only a kiosk-local failure (power, hardware) blanks a single screen,
> recoverable from the Fleet tab.

---

## 6. Fleet / Device Protocol

ExhibitOS inherits SignBoard's **two-protocol, bridged-not-unified** fleet model verbatim
(`signboard-fleet-management-spec.md`, `signboard-google-tv-spec.md`). The only domain
change is renaming and the addition of `device_class`.

### 6.1 Device classes

| `device_class` | Renders | Hardware | Protocol |
|---|---|---|---|
| `passive` | `card` or `video` | Pi Zero 2 W + monitor; legacy PC + monitor; Onn stick + TV; Google TV | Pi/legacy = WS; stick/TV = Fully Kiosk REST |
| `touchscreen` | `interactive` (also can do card/video) | touch panel driven by a Pi/legacy PC (Chromium touch) | WS (touch needs the agent + local browser) |

`device_class` gates the interactive form (D5/§3.3). `platform` (`pi` / `fully-kiosk` /
`legacy-pc`) selects the fleet protocol.

### 6.2 `display_device` table (ExhibitOS SQLite — renamed/extended SignBoard `kiosks`)

| column | type | notes |
|---|---|---|
| `id` | TEXT PK | hostname, e.g. `exhibit-main-gallery-card` |
| `room_slug` | TEXT | the room feed it subscribes to (replaces `channel_slug`) |
| `name` | TEXT | "Main Gallery — left wall" |
| `device_class` | TEXT | `passive` / `touchscreen` |
| `platform` | TEXT | `pi` / `fully-kiosk` / `legacy-pc` |
| `default_form` | TEXT | `card` / `video` / `interactive` |
| `assignment_form` | TEXT NULL | per-device form override (see §3.3) |
| `fully_kiosk_ip` | TEXT NULL | for `fully-kiosk` platform |
| `ip` | TEXT | last seen |
| `version` | TEXT | git short-SHA reported by agent |
| `online` | INTEGER | 0/1, computed from heartbeat/poll |
| `last_heartbeat` | INTEGER | epoch seconds |
| `uptime_seconds` / `memory_free_mb` / `load_avg_1m` | — | reported by Pi agent |
| `status` | TEXT | `active` / `maintenance` / `retired` |
| `created_at` | INTEGER | |

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

## 7. Render Targets — one Asset, four forms

All renderers read the **same cached Asset** from `content_cache` (Tier 1). No renderer
stores content. Each form is a React route/component under `client/src/display/`, served
at `GET /display/<room-slug>` with the form selected per §3.3.

### 7.1 Form 1 — Interpretive Card + QR (on-screen AND printable)

- **One shared HTML/CSS template** drives both the on-screen card and the printed sign.
  This is the crux of the Playwright decision (D7): the same Chromium renders both, so
  they cannot drift. Template id = `asset.card_template` (`infoage-house`).
- **Field mapping** (per PRD §6.1 / the canonical `museum-sign.md` house style):

| Sign element | Source |
|---|---|
| Title (big blue sans-serif, top-left) | `asset.title` |
| Hero photo + caption (upper-left) | `hero_image.file` (→ `/media/<id>`) + `hero_image.caption` |
| Inventor portrait + credit (upper-right) | `people[0].portrait` + `.name` + `.credentials` + `.role_label` |
| Bullets | `bullet_facts[]` |
| "The Backstory:" | `backstory` |
| QR + caption (lower-right) | QR(`qr_target_url` if set else `{qr_base_url}/{slug}`) |
| Closer / easter-egg strip | `closer` (renders the 3280→Onyx `related_assets` note) |
| Photo-slot list (production aid) | `media[]` with caption/source/credit |

- **On-screen:** the `/display/<room>` route renders this template full-screen for a
  `passive`+`card` device.
- **Print pipeline:** dashboard "Export printable card" → `POST /api/print/card/<asset_id>`
  → server runs **Playwright** headless Chromium, navigates to an internal render-only
  route `/_print/card/<asset_id>?template=infoage-house` (same template, print CSS
  `@page` sized to the InfoAge sign dimensions), `page.pdf()` → returns the PDF. **Runs
  server-side on the mini PC only** (Chromium bundled in the ExhibitOS image; never on
  kiosks). QR is rendered into the HTML via `qrcode` → data-URI so screen and print share
  one QR.

### 7.2 Form 2 — Video Information Display

- Renders on `passive` + `video`. Plays **self-hosted video** — a `media[]` item of type
  `video` served from the local mirror — via an **HTML5 `<video>` element** (looped,
  **muted autoplay**, museum-appropriate, optional ambient audio per assignment).
  **No YouTube/Vimeo iframe on any kiosk** (2026-06-01 policy): a YouTube embed on a public
  kiosk exposes the "Watch on YouTube" link + suggested-video end cards, letting a visitor
  escape into youtube.com. `asset.youtube_url` is phone/QR-side only. Browser-level
  navigation lockdown is the backstop (§9 / issue #37).
- **Room feed:** if a room (not a single asset) is assigned, cycles videos across the
  room's published assets in `asset.sort` order. Generalizes SignBoard's `PageCarousel`.
- Honors `room.operating_hours` for scheduled screen on/off (Pi via agent/HDMI-CEC; Fully
  Kiosk via its schedule). No demo video on missing content — error state.

### 7.3 Form 3 — Touchscreen Interactive

- Renders **only** on `device_class = touchscreen` (renderer-enforced gate, §3.3). A
  passive device handed this form refuses it and falls back to `default_form` + logs an
  error state.
- Visitor can scroll `interpretive_body` + `backstory`, swipe the `media[]` gallery (each
  with caption/source/credit), open `person` bios, and tap a `related_assets` link to
  jump to the related asset's interactive view (**3280 → Onyx 10000 traversal** and back).
- Idle timeout → attract/home screen (configurable seconds).

### 7.4 Form 4 — Dashboard (+ Fleet)

- React admin app (refactored SignBoard `client/src/admin/`). Content control: browse
  published Directus assets (read from Tier-1 cache), assign asset/room-feed → device with
  a chosen form, manage schedules + scheduled/emergency overlays (carried from SignBoard),
  trigger printable-card export.
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
- `POST /api/print/card/<asset_id>` (admin) → `services/print_service.py` launches
  Playwright, loads `http://localhost:8100/_print/card/<id>`, waits for fonts + images +
  QR, calls `page.pdf({format, printBackground:true, ...})`, streams the PDF back.
- Acceptance (PRD §6.1): editing a Directus field changes both the live card and the next
  export with no code change — guaranteed because both read the same cached Asset.

---

## 9. Refactoring the Seeded SignBoard Code

The seeded repo (`~/Workspaces/exhibit-os/server` + `client`) is SignBoard verbatim:
FastAPI + React + Tailwind + SQLite + WebSocket, with Wharfside-specific weather/marine
modules. The refactor has three buckets: **repurpose**, **remove/quarantine**, **rename**.

### 9.1 Repurpose (SignBoard tables/modules → ExhibitOS assignment + cache)

| SignBoard (today) | ExhibitOS | File-level action |
|---|---|---|
| `models/page.py` (`Page`, holds content body) | **`display_assignment`** — pointer to a Directus asset id + form + render options; **no content body** | Replace `Page` with `DisplayAssignment(id, room_slug, asset_id (Directus uuid) OR room_feed bool, form, render_options_json, sort, is_enabled)`. Drop `config_json`, `image_path`, `page_type`, `is_system`. |
| `models/channel.py` (`Channel`) | **`room` reference** — rooms are Directus content; ExhibitOS keeps only the device→room binding | Remove `Channel` as a content table; `room_slug` becomes a column on `display_device` + `display_assignment`. Keep the subscribe-by-slug routing. |
| `models/channel_page.py` (`ChannelPageAssignment`) | folded into `display_assignment` (sort/duration/enabled) | Migrate `sort_order`/`duration_override`/`is_enabled` onto `display_assignment`; delete `channel_page.py`. |
| SQLite content columns | **`content_cache`** (Tier-1 mirror of Directus) | New `models/content_cache.py` (`id, collection, slug, status, room_slug, data_json, updated_at`). |
| Overlay / schedule tables | **Unchanged** (scheduled + emergency overlays) | Keep — SignBoard's strength, carried forward as-is. (If currently embedded in `announcement`/`page`, extract into a dedicated `overlay` model.) |
| `kiosks` table + agent protocol | **`display_device`** + `device_class`/`platform` | Rename + extend per §6.2. WS manager (`ws/manager.py`, `ws/routes.py`) kept; rename channel→room, add `/ws/device-agent`. |
| `models/admin_user.py` + `api/auth.py` (JWT) | **Unchanged** — dashboard admin auth | Keep as-is for fleet + assignment control (D3: separate from Directus auth). |
| `services/settings_service.py` + `models/setting.py` | **Kept for ExhibitOS infra settings** (Directus URL, token, Fully Kiosk pw) | Keep; content-adjacent `qr_base_url`/`museum_name` move to Directus `setting` (§4.5). |
| `api/pages.py`, `api/channels.py` | **`api/assignments.py`**, **`api/display.py`** | Rewrite: `/api/display/<room-slug>` reads `content_cache` + `display_assignment`; `/api/assignments` is admin CRUD. |
| `client/src/display/PageCarousel.tsx`, `ChannelDisplay.tsx` | **`RoomDisplay.tsx`** + per-form components | Refactor routing to forms; reuse carousel for video room feeds + card sequences. |
| WebSocket `notify_page_update` | **`notify_content_changed(room_slug)`** | Rename; triggered by sync service, not by content edits (content edits happen in Directus now). |

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

### 9.4 New modules to add

- `server/services/directus_sync.py` — webhook handler + poll loop + media downloader.
- `server/services/directus_client.py` — thin httpx wrapper around Directus REST (read).
- `server/services/print_service.py` — Playwright card export.
- `server/api/sync.py` — `POST /api/sync/webhook`, `POST /api/sync/resync` (admin).
- `server/api/display.py` — `GET /api/display/<room-slug>` (reads cache + assignment).
- `server/api/assignments.py` — admin assignment CRUD.
- `server/api/print.py` — `POST /api/print/card/<asset_id>`.
- `server/models/content_cache.py`, `display_assignment.py`, `display_device.py`,
  `overlay.py`.
- `client/src/display/cards/InfoAgeHouseCard.tsx`, `VideoDisplay.tsx`,
  `TouchInteractive.tsx`, `RoomDisplay.tsx`.

---

## 10. Deployment Topology

### 10.1 Mini PC (the one server)

Docker Compose with **three** services on one bridge network:

```yaml
services:
  directus:        # System of Record
    image: directus/directus:latest
    depends_on: [directus-db]
    ports: ["8055:8055"]
    environment:
      DB_CLIENT: pg
      DB_HOST: directus-db
      KEY/SECRET, ADMIN_EMAIL/PASSWORD, PUBLIC_URL
      WEBSOCKETS_ENABLED: "false"     # ExhibitOS uses webhooks, not Directus WS
    volumes:
      - directus_uploads:/directus/uploads     # Directus media library (origin)

  directus-db:
    image: postgres:16-alpine
    volumes: [directus_pgdata:/var/lib/postgresql/data]

  exhibitos:       # Renderers + sync + fleet (refactored SignBoard)
    build: .
    depends_on: [directus]
    ports: ["8100:8100"]
    environment:
      DIRECTUS_URL: http://directus:8055
      DIRECTUS_TOKEN: ${DIRECTUS_TOKEN}        # read-published static token (D3)
      DIRECTUS_WEBHOOK_SECRET: ${...}
      DATABASE_URL: sqlite:////data/exhibitos.db
      MEDIA_DIR: /data/media
      JWT_SECRET_KEY, DEFAULT_ADMIN_PASSWORD
    volumes:
      - exhibitos_data:/data                   # SQLite + media mirror
    # Playwright Chromium bundled in this image (print, server-side only)
volumes: [directus_pgdata, directus_uploads, exhibitos_data]
```

- **Directus** owns its own Postgres + uploads volume (the media *origin*). ExhibitOS
  **mirrors** referenced media into `exhibitos_data:/data/media` (Tier 1) so displays
  never hit Directus.
- **ExhibitOS Dockerfile** gains a Playwright Chromium install layer (D7). Note the
  current `512M` memory limit (compose) must rise — Chromium for PDF export needs
  headroom; recommend **2 GB** for the exhibitos service, **1 GB** for directus,
  **1 GB** for postgres. A typical mini PC (8–16 GB) handles all three comfortably.
- Reverse proxy (Caddy/nginx, optional) terminates TLS and routes `/` → exhibitos,
  `/cms` → directus, so authors get a clean museum-branded Directus URL.

### 10.2 Kiosks

| Class | Device | OS/browser | Protocol | Tier-2 cache |
|---|---|---|---|---|
| passive card/video | Pi Zero 2 W + monitor (~$15) | Raspberry Pi OS + Chromium + `exhibit-agent` | WS | Service Worker + SD |
| passive card/video | Onn FHD stick (~$20) + any TV | Fully Kiosk (Chromium) | REST :2323 | Fully Kiosk webview cache + SW |
| passive (outdoor/polished) | Google TV | Fully Kiosk | REST :2323 | same |
| touchscreen | Pi/legacy PC + touch panel | Chromium + `exhibit-agent` | WS | Service Worker + disk |
| passive (repurposed) | legacy museum PC + monitor | Linux + Chromium + `exhibit-agent` (x86) | WS | Service Worker + disk |

Each kiosk points at `http://<minipc>:8100/display/<room-slug>` (or via reverse proxy /
Tailscale). Pi/legacy PC provisioned via refactored `scripts/kiosk/`; Fully Kiosk devices
via the 10-minute manual setup (`signboard-onn-fhd-kiosk-setup.md`, renamed).

### 10.3 Network assumptions

- All devices + mini PC on **one museum LAN** (InfoAge gallery network). Fully Kiosk REST
  (:2323) is **LAN-only**, never exposed publicly.
- Static IP/DHCP reservation per Fully Kiosk device (REST needs a stable IP).
- **Tailscale** (optional) for off-site admin: the mini PC is a subnet router/exit node;
  admin reaches the dashboard + (proxied) Fully Kiosk REST over the tailnet. Public QR
  targets resolve over the open internet (wiki/YouTube) — independent of LAN.
- No inbound public exposure of Directus or the dashboard required for v1 (admin is
  on-LAN or Tailscale). The only public surface is the QR deep-content host (external).

---

## 11. Non-Functional Requirements

### 11.1 Offline resilience (the headline NFR)

- **Directus down:** Tier-1 mirror serves all displays; dashboard shows a degraded-mode
  banner; authoring is paused (acceptable — content edits are infrequent). No display
  interruption.
- **Mini PC / LAN down:** Tier-2 Service Worker / Fully Kiosk cache keeps each kiosk on
  its last-known-good render; staleness indicator shown.
- **Never demo data** (PRD §8.3, feedback `no-demo-fallback`): on genuinely-missing
  content, every renderer shows a clear error state, not placeholder content.

### 11.2 Security

| Surface | Posture |
|---|---|
| **Public QR / deep content** | Read-only, external (wiki/YouTube). No ExhibitOS attack surface. |
| **ExhibitOS↔Directus** | Static **read-only**, published-only token (D3); LAN/tailnet only. Leak = exposure of already-public content. |
| **Directus admin/authoring** | Directus roles (Author/Reviewer/Admin); media-attribution enforced by Flow. On-LAN/tailnet. |
| **ExhibitOS dashboard** | Existing JWT admin auth; on-LAN/tailnet; not publicly exposed in v1. |
| **Fleet — Pi WS** | `DEVICE_AGENT_TOKEN` bearer on WS handshake; `update-scripts` restricted to a pinned repo/branch (no arbitrary command exec). |
| **Fleet — Fully Kiosk REST** | Per-device password (masked in ExhibitOS settings); LAN-only :2323; never proxied publicly. |
| **Display routes** | Unauthenticated read (kiosks need no login) but serve **published** content only (mirror is published-filtered). |
| **Kiosk navigation** | Locked to the ExhibitOS origin via Fully Kiosk URL allowlist + Chromium `URLAllowlist`/`URLBlocklist` policy; context menus disabled; no clickable off-origin links; kiosk video is self-hosted HTML5 (no YouTube iframe). Prevents visitors escaping into the open web (issue #37). |
| **Secrets** | Directus token, webhook secret, Fully Kiosk passwords, JWT key in env/`.env` + masked settings; per `credentials-apple-passwords` feedback, avoid plaintext credential files where a manager exists. |

### 11.3 Performance on cheap hardware

- **Pi Zero 2 W** renders a single static card / looping video — well within its means
  (SignBoard already proves this at Wharfside). Service Worker keeps it responsive offline.
- **Displays read from SQLite + local media** (Tier 1) — no per-request Directus round
  trip, no N+1 over the network. Room feed is a single indexed query + a JSON blob.
- **Playwright print is server-side only** and on-demand (not on render path) — its cost
  never touches kiosks.
- **Sync is delta-based** (webhook keys / `date_updated` poll) — no full re-pull on steady
  state.

### 11.4 Backup

- **Directus = the only thing that must be backed up** (it is the SoR). Nightly
  `pg_dump` of `directus-db` + a copy of `directus_uploads` to the museum's backup target
  (and/or Nick's Drive archive). Documented in the admin guide.
- ExhibitOS SQLite (`exhibitos_data`) is **regenerable** — `content_cache` + media rebuild
  from Directus on resync; only `display_assignment` + `display_device` are unique state,
  small, and included in the nightly backup for convenience (faster recovery than
  re-provisioning the fleet mapping).
- Recovery drill: restore Directus → bring up ExhibitOS → "Resync from Directus" → fleet
  reconnects. RPO ≤ 24h (nightly), RTO ≈ minutes (Compose up + resync).

---

## 12. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Directus free-tier license** conditioned on org < $5M revenue (PRD §9b #7) — InfoAge/VCF compliance + downstream museums | Med | High (could force a paid tier or relicense) | Confirm InfoAge/VCF qualifies (almost certainly — nonprofit); **document the licensing posture in the README** for downstream adopters; abstract the Directus client (`directus_client.py`) so a future swap to another OSS CMS (e.g. Payload, Strapi) is contained. **Flagged to Nick.** |
| R2 | **Playwright/Chromium bloat** on the mini PC image + memory | Med | Med | Print is server-side, on-demand, isolated; raise exibitos memory limit to 2 GB (§10.1); consider a separate `playwright` sidecar container if the main image gets unwieldy. |
| R3 | **Missed webhooks → stale displays** | Med | Low | 5-min poll safety net (D6) guarantees eventual consistency; "last sync" indicator surfaces staleness; manual resync button. |
| R4 | **Fully Kiosk auto-update breaks REST/kiosk mode** (noted in google-tv-spec) | Low | Med | Disable Play Store auto-update per device; validate on one device before fleet rollout. |
| R5 | **Author publishes uncredited media** (museum-grade attribution gap) | Med | Med | Directus Flow enforces caption+source+credit on status→published for `media_item`; reviewer gate. |
| R6 | **Two logins (Directus + dashboard)** annoys volunteers (D3) | Med | Low | Acceptable for v1; documented future SSO (Directus-as-IdP). The runbook makes it a one-time login each. |
| R7 | **Card print drift from on-screen** (the thing Playwright is meant to prevent) — regressions via diverging print CSS | Low | Med | Single shared component; print differences only in a print stylesheet, not a fork; visual review vs InfoAge's 9 signs is an explicit acceptance gate (PRD §6.1). |
| R8 | **Self-referential `related_assets` rendering loops** (3280→Onyx→3280) on touch interactive | Low | Low | Render "see also" as explicit navigation (not auto-expand); depth-1 traversal per tap; no recursive embed. |
| R9 | **Service Worker stale-bundle on iOS-style caches** (cf. feedback `ios-pwa-double-relaunch`) | Low | Low | `vite-plugin-pwa` autoUpdate + a visible app version; document the "two force-closes / reload" recovery in the runbook; Fleet "Reload" handles it remotely. |
| R10 | **Volunteer can't self-serve** (fails PRD §8 headline test) | Med | High | The whole D2/D4 design (assign-to-rooms, two clean surfaces) plus the required volunteer runbook (PRD §8.2); validate with a real InfoAge volunteer before "done." |
| R11 | **Media mirror disk growth** on the mini PC (self-hosted videos) | Med | Med | Kiosk video is self-hosted (no YouTube on kiosks, 2026-06-01 policy), so video binaries live on the mirror: stream downloads to disk (no in-memory buffering), serve with HTTP range, mirror only what's referenced by published assets, prune orphans aggressively on resync, and monitor disk. |

---

## 13. v1 Build Order (for dev-planning handoff)

1. **Refactor & rename** (§9): strip Wharfside modules, rename SignBoard→ExhibitOS,
   replace Page/Channel with `display_assignment`/`display_device`/`content_cache`.
2. **Stand up Directus** in Compose (§10.1) with the §4 content model + roles + Flows.
3. **Sync service** (`directus_sync.py` + `directus_client.py`): webhook + poll + media
   mirror → `content_cache`.
4. **Display API + RoomDisplay** routing; **Card renderer** (`InfoAgeHouseCard`).
5. **Playwright print** (`print_service.py`) — prove screen/print parity on the 3280 card.
6. **Video + Touch interactive** renderers (touch gate).
7. **Fleet**: rename agent → `exhibit-agent`, `/ws/device-agent`, Fully Kiosk bridge,
   Fleet tab.
8. **Author the Concurrent 3280** end-to-end in Directus (incl. Onyx 10000
   `related_assets`); render on 1–2 real InfoAge displays.
9. **Handoff package** (§8): volunteer runbook + admin setup guide; validate with a real
   volunteer.

---

## 14. Open Items to Relay to Nick (orchestrator → Nick)

1. **Directus license tier (R1, PRD §9b #7) — needs a human confirmation.** Confirm
   InfoAge/VCF is under the $5M revenue threshold (nonprofit — near-certain) and decide
   how to phrase the licensing posture in the README for downstream museum adopters.
2. **Postgres for Directus (D2)** is a new dependency vs. SignBoard's SQLite-only world —
   it's standard for Directus prod and runs fine on the mini PC, but it does mean a second
   DB engine in the stack. Confirm acceptable (recommended yes).
3. **Two logins for v1 (D3/R6).** Authors log into Directus; admin logs into the ExhibitOS
   dashboard. Simpler for v1; SSO is a documented Phase-2 improvement. Confirm OK.
4. **Mini PC memory headroom (R2).** Three services + bundled Chromium want ~4 GB
   allocated. Confirm the target mini PC has the RAM (8 GB+ recommended).
5. **Kiosk video = self-hosted HTML5 (RESOLVED 2026-06-01).** Kiosks never embed YouTube
   (escape risk on public/touch screens); they play self-hosted `<video>` from the mirror.
   YouTube is reserved for the phone/QR deep-content page. Media mirror now holds video
   binaries (R11), and a browser-level URL-allowlist lockdown (issue #37) is the backstop.

---

## 15. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-05-31 | Software Architecture (AI-assisted) | Initial architecture. Resolved PRD §9b auth (static read-only token), device-location (ExhibitOS-only, assign-to-rooms), and form precedence (assignment>default, class-gated). Concrete Directus model, two-tier cache design, fleet protocol, render targets, SignBoard refactor map, deployment topology, NFRs, risks. |
