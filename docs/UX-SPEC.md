# UX Design Specification: ExhibitOS

**Version:** 0.2
**Date:** 2026-06-01
**Author:** Nick DeMarco, with AI assistance
**Status:** Draft
**PRD Reference:** `docs/PRD.md` (v0.3)
**Wiki Reference:** `wiki/projects/concurrent-3280-museum/museum-sign.md`

---

## 1. Executive Summary

### 1.1 Design Vision

ExhibitOS surfaces one authoring surface and three display surfaces, bound together by a single content record. The curator writes once in Directus; the visitor reads from a physical card, a passive video screen, or a touchscreen kiosk; the dashboard connects the two. Every design decision in this document serves that constraint.

The visual language is deliberately neutral — warm off-white paper tones that evoke a reading environment, not a tech product. The museum's content (photos, prose, artifacts) is the spectacle. ExhibitOS's chrome is the frame.

### 1.2 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Directus authoring UX | Field grouping with contextual help text, not custom forms | Non-technical volunteers; Directus's native UI is already battle-tested for this. Custom forms would require maintenance. |
| Card layout model | **Two fixed designed canvases — landscape 1920×1080 and portrait 1080×1920 — scaled-to-fit** (DisplayCanvas extended with a `portrait` design size) | Consistent cross-device rendering at distance; full portrait support in v1 (ARCHITECTURE §6a, 2026-06-01). A portrait sign is a distinct composition, not a rotated landscape. |
| Per-display Display Profile | **Profile = orientation + resolution + DPR (auto-detected) + physical size + viewing distance (manual) + class** | Drives orientation layout + physical text-scale so one Asset is legible on a 24″ desk monitor and a 75″ wall TV (ARCHITECTURE §6a). |
| Video / touch layout model | **Responsive to the actual viewport (no fixed canvas)** | Video `object-fit: contain`; touch fluid grid. Adapt to any resolution/orientation/4K without bars (ARCHITECTURE §6a.2). |
| Text legibility | **Scaled from physical size + viewing distance, not pixels** (root rem from profile) | Preserves ADA distance-viewing minimums across screen sizes (ARCHITECTURE §6a.3 / UX §8.1). |
| Print and screen card | One HTML/CSS template, Playwright headless export | PRD §9a locked this. No drift between on-screen and print. |
| Interpretive card structure | Mirrors InfoAge 9-sign portfolio exactly | Physical sign cohesion is a PRD AC. Deviation breaks the museum portfolio. |
| Interactive idle reset | 90 seconds, returns to attract screen | Long enough for reading, short enough to reset for the next visitor. |
| Dashboard device model | Rooms as the assignment target; devices are fleet-only | Aligns with PRD §9b lean: devices live in ExhibitOS SQLite; authors never see device hostnames. |
| Empty/error state policy | Error message + last-cached content; never demo data | PRD §8 and §9a hard requirement. |
| Typography for distance | Title 72px+, body 28-32px minimum **at the baseline profile (24″ @ 5ft); scaled by the profile root rem on larger/farther screens** | ADA museum standard; readable at 1.5m standing distance and preserved on 75″ wall TVs via the text-scale rule (ARCHITECTURE §6a.3). |

### 1.3 Design Principles

1. The content is the product. ExhibitOS chrome must recede.
2. Volunteers succeed without help desks. Every authoring step is self-explanatory from the UI.
3. One truth, many surfaces. No field is repeated; every render derives from the same record.
4. Kiosks must degrade gracefully, never go blank. Last-known-good beats white screen.
5. Touch targets are for hands at arm's length, not for mice. Minimum 64px, preferably 88px.

---

## 2. Personas (Summary)

These expand on PRD §3; abbreviated here for reference.

### 2.1 Doug — Curator / Volunteer Author

Non-technical. Comfortable with web forms and word processors. Will use Directus's admin UI to write exhibit records, upload photos, and submit for review. Will use the ExhibitOS dashboard to assign exhibits to displays and export print-ready cards. Success criterion: completes the full workflow from the runbook without calling a developer.

### 2.2 Maria — Museum Visitor

Standing at or walking past an exhibit. Reads the card (30 seconds), optionally taps the touchscreen (a few minutes), optionally scans the QR. Touch targets must be reachable from standing distance. Text must be legible at 1–2 meters.

### 2.3 Nick / Future Admin

Provisions hardware and Docker once. Rarely touches the system after handoff. Uses the Fleet tab for recovery only.

---

## 3. Directus Authoring UX

Directus provides a configurable admin UI where fields can be grouped, labelled, and annotated with help text. This section specifies exactly how each collection should be configured so that Doug can author an exhibit without confusion.

### 3.1 Principle: configure Directus, do not replace it

The goal is a thoughtfully configured content model in Directus's native admin — not a custom form app. Each specification below is a Directus field-configuration instruction (group name, field label, help text, required flag, interface type), not a custom-built component.

### 3.2 Collection: Asset — field layout and grouping

The Asset collection is the central authoring surface. Configure it with four field groups presented in top-to-bottom order on the Directus detail form.

---

**Group 1: Identity** (always visible at the top)

| Field | Display label | Interface | Required | Help text |
|---|---|---|---|---|
| `title` | Exhibit title | Text input | Yes | "The name displayed large at the top of the sign. E.g. 'The Concurrent 3280'" |
| `subtitle` | Subtitle / tagline | Text input | No | "A one-line description that appears under the title. E.g. 'The last great pre-RISC scalar minicomputer'" |
| `slug` | URL slug | Text input (auto-generated from title) | Yes | "Used in QR codes and URLs. Generated automatically — only change it if the title changes significantly." |
| `status` | Status | Dropdown (Draft / In Review / Published / Archived) | Yes | "Set to Draft while writing. Submit for review when ready. Only Published exhibits appear on displays." |
| `featured` | Featured | Toggle | No | "Pin this exhibit to the top of dashboard lists." |

---

**Group 2: The Card** (collapsible, open by default)

This group contains every field rendered on the interpretive card. Label the group "Interpretive Card Content" so Doug knows exactly what this drives.

| Field | Display label | Interface | Required | Help text |
|---|---|---|---|---|
| `hero_image` | Hero photo | Relation (to media_item) | Yes | "The main photograph displayed on the upper-left of the sign. Create a Media Item first, then select it here." |
| `bullet_facts` | Key facts (bullet list) | Repeater / JSON (one text line per item) | Yes (min 3) | "Short facts shown as bullets on the sign. Write each as a complete, standalone sentence. 6–10 bullets works well." |
| `interpretive_body` | Main story | Rich text / Markdown | Yes | "The narrative paragraph(s) on the sign. 150–250 words is typical for the InfoAge house style." |
| `backstory` | Backstory section | Rich text / Markdown | No | "Appears under the 'The Backstory:' header on the sign. Provides deeper historical context." |
| `closer` | Closing line | Text input | No | "The single memorable sentence in the bottom strip. E.g. 'Designed in NJ. Built in NJ. The architect who built it shaped the chip that replaced it.'" |
| `card_template` | Print style | Dropdown (InfoAge House / Generic) | Yes | "Choose 'InfoAge House' to match the existing signs at the VCF museum." |

---

**Group 3: Deep Content & QR** (collapsible)

| Field | Display label | Interface | Required | Help text |
|---|---|---|---|---|
| `qr_target_url` | QR destination URL | URL input | No | "Leave blank to use the default (base URL + slug). Override only if the deep content page has a specific permanent URL." |
| `deep_content_url` | Deep content page | URL input | No | "The wiki or web page this exhibit's full story lives on (linked from QR and touchscreen)." |
| `youtube_url` | YouTube video URL | URL input | No | "Full YouTube URL — embedded on the **phone/QR deep-content page only**. On-floor video screens play the self-hosted video file you upload as a Video media item, not YouTube." |

---

**Group 4: Relations** (collapsible)

| Field | Display label | Interface | Required | Help text |
|---|---|---|---|---|
| `room` | Room / Location | Relation (to Room) | No | "Which gallery or room this exhibit is physically located in." |
| `people` | People (inventors, architects) | Many-to-many relation (to Person) | No | "Link the people associated with this exhibit. Their portrait and credentials appear on the card." |
| `media` | Gallery images | Many-to-many relation (to Media Item) with sort | No | "Additional photos for the touchscreen gallery. Drag to reorder. The hero photo does not need to be repeated here." |
| `related_assets` | Related exhibits | Self-referential M2M (to Asset) with note | No | "Link exhibits that tell a connected story. Add a short note explaining the connection. E.g. 'Same architect, 30 ft away.'" |

---

### 3.3 Collection: Media Item — field layout

Media Items are created before being attached to an Asset. Configure the form with one group:

| Field | Display label | Interface | Required | Help text |
|---|---|---|---|---|
| `file` | Upload file | File upload | Yes (for image/video) | "Upload the image or video file. For YouTube/Vimeo, use 'External Video' type and paste the URL instead." |
| `media_type` | Type | Dropdown (Image / Video / External Video) | Yes | "Choose 'External Video' for YouTube or Vimeo links — no file upload needed." |
| `external_url` | External video URL | URL input | Conditional on media_type = external_video | "Paste the full YouTube or Vimeo URL." |
| `caption` | Caption | Text input | Yes (for published) | "Displayed under the photo on signs and in the gallery. Describe what is shown." |
| `source` | Source / provenance | Text input | Yes (for published) | "Where this image came from. E.g. 'Drive archive — 1985 lab shoot' or 'techmonitor.ai archive'" |
| `credit` | Credit / attribution | Text input | Yes (for published) | "Who to credit. E.g. 'Photo by Nick DeMarco, 1985' or 'Courtesy InfoAge Science Center'" |
| `alt_text` | Alt text (accessibility) | Text input | No | "A brief description for screen readers and if the image fails to load." |

---

### 3.4 Collection: Person — field layout

| Field | Display label | Interface | Required | Help text |
|---|---|---|---|---|
| `name` | Full name | Text input | Yes | "E.g. 'Ken Yeager'" |
| `credentials` | Credentials / degree | Text input | No | "E.g. 'MIT '72' — shown in small text next to the name on the sign." |
| `role_label` | Role at this museum | Text input | No | "E.g. 'Architect of the 3280' — the one-line descriptor on the sign." |
| `lifespan` | Lifespan | Text input | No | "E.g. '1949–2017' — displayed with the portrait if provided." |
| `portrait` | Portrait photo | Relation (to Media Item) | No | "Headshot displayed upper-right on the interpretive card." |
| `bio` | Full biography | Rich text | No | "Shown in the touchscreen interactive's person detail view." |

---

### 3.5 Collection: Room — field layout

| Field | Display label | Interface | Required | Help text |
|---|---|---|---|---|
| `name` | Room name | Text input | Yes | "E.g. 'VCF Main Gallery'" |
| `slug` | Display feed URL | Text input (auto) | Yes | "Displays subscribe to /display/[slug]. Auto-generated — change with care; it will break existing screen subscriptions." |
| `description` | Room description | Text area | No | "Optional intro text for the room." |
| `operating_hours` | Operating hours | JSON (or structured repeater) | No | "Per-day open/close times used for automatic screen on/off. Leave blank for always-on." |

---

### 3.6 Add a New Exhibit — Happy Path (end-to-end authoring flow)

This is the step-by-step user journey for Doug authoring the Concurrent 3280 from scratch. Every step happens in Directus.

**Prerequisites:** Doug has a Directus account with the Author role. He has the hero photo and portrait ready as files on his computer.

---

**Step 1: Create the Media Items (photos first)**

Doug navigates to Content > Media Items > Create New.

He fills in:
- File: uploads the 1985 lab photo (the hero image)
- Type: Image
- Caption: "Concurrent 3280 cabinet, Tinton Falls NJ engineering lab, December 1985"
- Source: "Drive archive — Nick DeMarco personal collection"
- Credit: "Photo by Nick DeMarco, 1985"
- Alt text: "Large 1980s minicomputer cabinet in an engineering lab"

He saves. He repeats for the Yeager portrait (to use in the Person record), and for each additional gallery photo.

Why photos first: the Asset form's hero_image field is a relation — Doug needs the Media Item to exist before he can link it. The help text on the hero_image field reads: "Create a Media Item first, then select it here." This is the one authoring-order dependency and the runbook must make it explicit.

---

**Step 2: Create the Person record (Ken Yeager)**

Doug navigates to Content > People > Create New.

He fills in:
- Name: Ken Yeager
- Credentials: MIT '72
- Role label: Architect of the 3280
- Lifespan: 1949–2017
- Portrait: selects the Yeager Media Item created in Step 1

He saves.

---

**Step 3: Create the Asset record**

Doug navigates to Content > Assets > Create New.

**Group 1 — Identity:**
- Exhibit title: The Concurrent 3280
- Subtitle: The last great pre-RISC scalar minicomputer
- Slug: concurrent-3280 (auto-generated; Doug leaves it)
- Status: Draft

**Group 2 — The Card:**
- Hero photo: selects the 1985 lab photo Media Item
- Key facts (bullets): Doug types each bullet as a line in the repeater
- Main story: types the interpretive body
- Backstory: types the Backstory section
- Closing line: "Designed in NJ. Built in NJ. The architect who built it shaped the chip that replaced it. And both machines now sit retired in this museum — about thirty feet apart."
- Print style: InfoAge House

**Group 3 — Deep Content & QR:**
- QR destination URL: leaves blank (will use base URL + slug)
- YouTube video URL: pastes the YouTube video URL

**Group 4 — Relations:**
- Room: selects "VCF Main Gallery"
- People: clicks Add, searches "Yeager", selects Ken Yeager
- Gallery images: adds the Schottky TTL board photo and the Onyx 10000 photo
- Related exhibits: clicks Add, types "Onyx", selects "SGI Onyx 10000", adds note "Same architect — Ken Yeager designed the MIPS R10000 that powers it. 30 ft from this machine."

Doug saves as Draft.

---

**Step 4: Submit for review**

Doug changes Status from Draft to In Review. Directus notifies the Reviewer role (configured in Directus's notification settings). The reviewer opens the record, reads it, and changes Status to Published. If changes are needed, the reviewer comments in Directus's built-in comments panel and sets status back to Draft.

Doug receives a notification. He makes edits, saves, sets back to In Review.

---

**Step 5: Assign to a display (in the ExhibitOS dashboard)**

Once Published, Doug opens the ExhibitOS dashboard (separate URL, separate login for v1). He navigates to Rooms > VCF Main Gallery. He sees the "Main Gallery — left wall" display. He clicks "Assign Content", selects "The Concurrent 3280" from the published assets list, chooses Form: Card. He saves. The display immediately shows the card (via WebSocket push or 60s poll). Done.

> The display's **Display Profile** (resolution/orientation/DPR) is auto-detected the first time the screen connects, and its physical size + viewing distance were entered once by the admin at provisioning (§7.4a). Doug never touches the profile — the card automatically renders in the right orientation at the right text scale. If the display is a portrait sign, Doug's identical "assign card" action yields the portrait card composition (§4.2a) with no extra step.

---

**Step 6: Export the printable card (in the ExhibitOS dashboard)**

Doug navigates to Assets > The Concurrent 3280. He clicks "Export printable card". The dashboard POSTs to the ExhibitOS server, which runs Playwright headless against the card renderer URL, and returns a PDF download. Doug saves the PDF and sends it to the museum's print vendor.

---

**Fix a typo (the simplest journey):**

Doug opens Content > Assets > The Concurrent 3280 in Directus. He edits the field. He saves. The on-screen card updates on the next content refresh (server poll from Directus, then pushed to displays). No other step needed.

---

## 4. Interpretive Card — On-Screen and Printable

### 4.1 Design Principles for the Card

The card is a museum sign rendered on a screen. It must look like it belongs alongside InfoAge's existing ENIAC / UNIVAC / Wang signs, not like a web app.

- Warm off-white background (#FAF7F2), not pure white. Evokes archival paper.
- Blue headings: InfoAge house blue, approximately #1A3A6B (to match existing signage; calibrate against physical signs on first print review).
- Serif body text for narrative sections: readability at distance and visual continuity with printed signs.
- Sans-serif for titles, bullets, and metadata labels.
- No drop shadows, no rounded cards, no gradients. Flat, print-like.
- All content areas have clear typographic hierarchy: title > subtitle > section headers > body > captions > credits.

### 4.2 On-Screen Card Layout (1920x1080 canvas)

The canvas follows the existing DisplayCanvas component (1920x1080, CSS-transform scaled to viewport). The card renders full-screen within this canvas.

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ BACKGROUND: warm off-white #FAF7F2                                                   │
│                                                                                      │
│ ┌──────────────────────────────────────────────────────────────────────────────────┐ │
│ │  TITLE BAR  — full width, InfoAge blue background (#1A3A6B), 80px tall           │ │
│ │  Title text: white, 64px, bold sans-serif, left-padded 48px                      │ │
│ │  Subtitle: white, 28px, light weight, immediately right of or below title        │ │
│ └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  LEFT COLUMN (55% width)                  RIGHT COLUMN (40% width, right-padded)    │
│  ┌────────────────────────────────────┐   ┌──────────────────────────────────────┐  │
│  │ HERO PHOTO                         │   │ INVENTOR PORTRAIT                    │  │
│  │ Full column width                  │   │ 280x280px, centered                  │  │
│  │ ~380px tall (16:9 or fill)         │   │                                      │  │
│  │ Caption below: 18px serif italic   │   │ Name: 26px bold sans                 │  │
│  │ Credit: 14px gray                  │   │ Credentials: 18px gray               │  │
│  └────────────────────────────────────┘   │ Role: 18px italic                    │  │
│                                           │                                      │  │
│  BULLETS SECTION                          │ (Lifespan if provided, 16px gray)    │  │
│  Section label: "AT A GLANCE"             └──────────────────────────────────────┘  │
│  12px uppercase tracking, InfoAge blue                                               │
│  ┌────────────────────────────────────┐   BACKSTORY SECTION                         │
│  │ • Bullet fact (28px, semi-bold)    │   Label: "THE BACKSTORY:"                   │
│  │ • Bullet fact                      │   16px uppercase tracking, InfoAge blue     │
│  │ • Bullet fact                      │   ┌──────────────────────────────────────┐  │
│  │ • ... (6–10 bullets)               │   │ Backstory text                       │  │
│  └────────────────────────────────────┘   │ 22px serif, line-height 1.5          │  │
│                                           │ (3–6 sentences typical)              │  │
│  INTERPRETIVE BODY                        └──────────────────────────────────────┘  │
│  22px serif, line-height 1.6                                                         │
│  (150–250 words)                          QR CODE                                   │
│                                           ┌──────────────────────────────────────┐  │
│                                           │ QR: 180x180px                        │  │
│                                           │ Caption below: 18px serif italic     │  │
│                                           │ "Scan for the full story..."         │  │
│                                           └──────────────────────────────────────┘  │
│                                                                                      │
│ ┌──────────────────────────────────────────────────────────────────────────────────┐ │
│ │  CLOSER STRIP — full width, dark navy background (#0B1F3A), 72px tall            │ │
│ │  Closer text: white or warm gold, 26px italic serif, centered, padded 48px H     │ │
│ └──────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Column gutters:** 48px between left and right columns, 48px outer margin.
**Vertical rhythm:** 24px between sections within a column.
**Overflow handling:** If bullet list or body text overflows its zone, reduce font size to 24px as a first step, then 20px as a minimum floor. Never clip content. If content still overflows at 20px, truncate the interpretive body with an ellipsis and a "Full story: scan QR" note.

> **Profile note.** This is the **landscape** canvas (`1920×1080`), selected when `profile.orientation = landscape`. Px sizes above are at the **baseline profile** (24″ @ 5 ft); the renderer sets the CSS root rem from the profile `text_scale` (ARCHITECTURE §6a.3) so the same canvas stays legible on a 75″ wall TV. The whole canvas is then CSS-transform scaled-to-fit the actual viewport (letterbox/pillarbox on odd aspect ratios), reusing the seeded `DisplayCanvas`.

---

### 4.2a Portrait Card Layout (1080x1920 canvas) — v1

When `profile.orientation = portrait`, the card renders a **distinct portrait composition** on a `1080×1920` designed canvas (not a rotated landscape). It carries the same structural elements as the landscape card and the same InfoAge house style — title / hero+portrait / bullets / backstory / QR / closer — **reflowed top-to-bottom for a tall canvas** (single column, no left/right split). This mirrors the physical InfoAge house style adapted to a portrait sign.

```
┌────────────────────────────────────────────────┐ 1080 wide
│  TITLE BAR — full width, InfoAge blue, 120px    │
│  Title: white, 72px bold sans, left-pad 56px    │
│  Subtitle: white, 32px light, below title       │
├────────────────────────────────────────────────┤
│  HERO PHOTO — full width, ~640px tall (fill)    │
│  Caption: 22px serif italic, pad 32px           │
│  Credit: 16px gray                              │
├──────────────────────────┬─────────────────────┤
│  INVENTOR PORTRAIT        │  (portrait sits      │
│  320×320px, left          │   beside its meta,   │
│  Name: 30px bold sans     │   one band, not a    │
│  Credentials: 22px gray   │   full second column)│
│  Role: 22px italic        │                     │
│  Lifespan: 18px gray      │                     │
├──────────────────────────┴─────────────────────┤
│  AT A GLANCE  (label 16px uppercase, blue)      │
│  • Bullet fact (32px semi-bold)                 │
│  • Bullet fact                                  │
│  • ... (6–10 bullets, full width)               │
├────────────────────────────────────────────────┤
│  INTERPRETIVE BODY                              │
│  26px serif, line-height 1.6, full width        │
│  (150–250 words)                                │
├────────────────────────────────────────────────┤
│  THE BACKSTORY:  (label 18px uppercase, blue)   │
│  24px serif, line-height 1.6, full width        │
├──────────────────────────┬─────────────────────┤
│  QR CODE                  │  "Scan for the       │
│  220×220px, left          │   full story…"       │
│                           │  20px serif italic   │
├──────────────────────────┴─────────────────────┤
│  CLOSER STRIP — full width, dark navy, 110px    │
│  Closer: white/gold, 28px italic serif, centered│
└────────────────────────────────────────────────┘ 1920 tall
```

**Layout rules (portrait):**
- **Single primary column** at full canvas width (56px outer margins). The two places that pair side-by-side (portrait+meta, QR+caption) are *bands* within the single column, not a true two-column split — this keeps the tall reading flow uninterrupted.
- **Vertical order is the narrative order:** title → hero → inventor → bullets → body → backstory → QR → closer. (Landscape splits this into two columns; portrait stacks it.)
- **Section rhythm:** 32px between stacked sections (vs. 24px landscape — more vertical room).
- **Overflow handling:** same ladder as landscape — bullets/body reduce 32→28→24px (portrait floor 24px, larger than landscape's 20px because the wider single column needs fewer reflows), then ellipsis + "Full story: scan QR".
- **Scale-to-fit + text-scale:** the `1080×1920` canvas is CSS-transform scaled to the actual portrait screen (pillarbox/letterbox on odd aspect ratios); type is authored in rem and the root rem comes from the profile `text_scale` (ARCHITECTURE §6a.3), preserving ADA minimums.
- **Print:** the printable export uses this same portrait canvas when `orientation=portrait` is selected in the export dialog (ARCHITECTURE §7.1), so a portrait on-screen sign and its printed counterpart match.

---

### 4.3 Concrete Layout: Concurrent 3280

This is the worked example showing how the field values map to the card layout.

**Title bar:**
- Title: "The Concurrent 3280" — 64px white bold sans on InfoAge blue
- Subtitle: "The last great pre-RISC scalar minicomputer" — 26px white light

**Left column, hero photo:**
- File: 1985 Tinton Falls lab photo (from `hero_image` Media Item)
- Caption: "Concurrent 3280 cabinet, photographed in the Tinton Falls NJ engineering lab, December 1985"
- Credit: "Photo by Nick DeMarco, 1985"

**Right column, portrait:**
- Photo: Ken Yeager headshot (from `people[0].portrait`)
- Name: "Ken Yeager"
- Credentials: "MIT '72"
- Role: "Architect of the 3280"
- Lifespan: "1949–2017"

**Left column, bullets ("AT A GLANCE"):**
The first six bullets from `bullet_facts[]`, rendered in order. Example:
- "The last great pre-RISC scalar minicomputer."
- "Designed in New Jersey during the Perkin-Elmer to Concurrent Computer transition (Nov 1985 spinoff)."
- "Released January 26, 1988 — 3280SP single-processor, 6 MIPS."
- "November 29, 1988 — 3280E MPS, up to 12 processors, 76.8 MIPS, 256 MB RAM."
- "Built from Schottky TTL discrete logic — anachronistic by 1988, but proven for real-time work."
- "Ken Yeager (MIT '72) later architected the MIPS R10000 — the chip inside the Onyx 10000, thirty feet from here."

**Left column, interpretive body:**
From `interpretive_body`. 180 words, 22px serif.

**Right column, backstory:**
From `backstory`. Prefixed with "THE BACKSTORY:" label.

**Right column, QR:**
QR encodes `{qr_base_url}/concurrent-3280`. Caption from the fixed string: "Scan for the full story: the engineers, the architecture, the lab photos, and what came next."

**Closer strip:**
"Designed in NJ. Built in NJ. The architect who built it shaped the chip that replaced it. And both machines now sit retired in this museum — about thirty feet apart."

---

### 4.4 Printable Card Layout

The printable card uses the same HTML/CSS template as the on-screen card, rendered by Playwright at the same 1920x1080 canvas, then exported as a PDF at 150–200 DPI (for sign printing, the dev team should confirm the target print size with InfoAge; a standard 24"x36" museum sign prints well at 150dpi from a 1920x1080 canvas if upscaled, but InfoAge may want a higher-resolution CSS canvas — flag this to Nick).

**Print-specific overrides:**
- Remove the cursor, any hover states, and WebSocket status indicators.
- Replace the warm-off-white background with true white (#FFFFFF) so the printer does not waste ink on a tinted background unless the museum explicitly requests the tinted stock.
- Embed all fonts (do not rely on Google Fonts CDN at print time — bundle the font files in the Docker image).
- QR code renders at sufficient resolution for scanning from a printed sign (min 2cm x 2cm at final print size; scale up accordingly in the CSS).

**Visual match requirement (PRD AC):** The printable card must be reviewed by InfoAge/VCF staff (Jeff Brace or Doug Crawford) alongside the existing nine signs before v1 ships. The UX designer (or dev team) should make a PDF proof and a side-by-side photo comparison. The primary checklist items:
- Title bar color matches.
- Bullet font and weight match.
- Portrait placement and cropping match.
- Closer strip color and text treatment match.
- QR is in the lower-right quadrant.

---

### 4.5 On-Screen Card: States

**Normal (content loaded):**
Full card as described above. No animated elements. Static display.

**Loading (first fetch in progress):**
Same warm off-white canvas. Title bar placeholder (InfoAge blue, full width). Content areas show subtle shimmer placeholder blocks (CSS animation, same colors — no spinners, which look out of place on a museum sign). Text: none. Duration: typically under 2 seconds on LAN.

**Last-known-good (Directus unreachable, cache available):**
Card renders from local cache exactly as if live. A small status bar at the very bottom of the closer strip (below the closer text, 12px, white/40% opacity): "Content from [date/time]. Reconnecting..." This is subtle enough not to distract visitors but visible to a curator doing a walkthrough.

**Error (Directus unreachable, no cache):**
```
┌─────────────────────────────────────────────┐
│  [Title bar — InfoAge blue — empty title]   │
│                                             │
│         EXHIBIT CONTENT UNAVAILABLE         │
│                                             │
│    This display is reconnecting.            │
│    Please check the system status           │
│    in the ExhibitOS dashboard.              │
│                                             │
│    [Room name] · [Display name]             │
│    Last attempt: [time]                     │
│                                             │
│    Retrying every 60 seconds.               │
└─────────────────────────────────────────────┘
```
Font size: 32px. Text centered vertically. Background: dark navy (prevents a blinding white screen if a projector is involved). No spinner — the retry message is sufficient.

**Unpublished/unassigned:**
If a display has no assignment, or the assigned asset is in Draft status: same error-state layout, message: "No exhibit assigned to this display." This informs the curator and does not show any content.

---

## 5. Video Information Display

### 5.1 Purpose and Context

A passive screen in the exhibit room plays **self-hosted video** full-screen, looped, muted by default, via an HTML5 `<video>` element. It runs on a `passive` device with `default_form = video`. The source is the Asset's self-hosted `video` media item (served from the local mirror); if a room is assigned instead of a single asset, it cycles across all published assets' self-hosted videos in order. **No YouTube/Vimeo iframe runs on a kiosk** (2026-06-01 policy — public-kiosk escape risk); `youtube_url` drives only the phone/QR deep-content page. Browser-level nav lockdown: issue #37.

### 5.2 Layout: Attract / Idle State

When a display first loads, before the video begins, or when cycling between videos in a room playlist:

```
┌───────────────────────────────────────────────────────────┐
│                                                           │
│                                                           │
│   [Museum logo or room name — centered, white text]       │
│                                                           │
│   [Exhibit title, if single-asset assignment]             │
│   60px white, light weight, centered                      │
│                                                           │
│   "Video loading..."  — 28px, white/60%                   │
│                                                           │
└───────────────────────────────────────────────────────────┘
Background: #0B1F3A (dark navy)
```

This attract state appears for at most 3 seconds while the video buffers. It is not a permanent idle screen; the video plays as soon as it is ready.

### 5.3 Layout: Playing State

Full-screen video, no browser chrome. Black letterbox bars (natural from the video player) if the video aspect ratio does not match the screen.

**Overlay strip (bottom, always visible):**
A semi-transparent dark strip (48px tall, rgba(0,0,0,0.55)) at the bottom of the screen carries:
- Left: Exhibit title — 24px white bold
- Right: Room name — 18px white/70%
- Far right: small loop indicator (three dots cycling) so a curator can tell the display is alive

This strip is subtle enough that visitors focused on the video will not find it distracting, but a curator doing a walkthrough can confirm which exhibit is playing.

**Captions:**
Since kiosk video is self-hosted HTML5 `<video>`, captions come from an optional sidecar WebVTT `<track>` file attached to the asset (or are burned into the video at production time). There is no reliance on a video platform's native caption UI. If no caption track is provided, the video plays without captions.

### 5.4 Looping Behavior

Single-asset assignment: the video replays immediately on end. No pause, no interstitial.

Room assignment (multiple assets with videos): each asset's video plays once, then advances to the next asset in the room's published-asset list (sorted by `sort_order` or alphabetically if no sort is defined). After the last asset's video, it cycles back to the first. A 2-second black interstitial between items prevents a jarring cut.

If an asset has no `youtube_url` and no video media items, it is skipped in the room playlist (not an error; just skipped).

### 5.5 States

**Normal (video playing):** As above.

**Buffering (>3 seconds):** A subtle pulsing dot in the lower-right corner of the overlay strip signals buffering. The attract state does not re-appear.

**No content (no video found for assigned asset/room):**
```
Dark navy background.
"No video assigned to this display."
28px white, centered.
Room name and display name below, 20px white/50%.
"Contact the curator to assign a video exhibit."
```

**Directus unreachable, cache available:** The video URL from cache plays normally. Cache-miss for the URL itself: show the no-content state.

**Operating hours (screen off):** The Pi agent or Fully Kiosk schedule powers the physical display off. When the display comes back on, the video resumes from the beginning.

---

## 6. Touchscreen Interactive

### 6.1 Device Gating

The interactive form renders only on devices with `device_class = touchscreen`. If a passive device is assigned the interactive form, the renderer checks the device class at load time and falls back to the device's `default_form` (card or video), displaying a brief warning in the closer strip: "Interactive form requires a touchscreen display. Showing card instead."

The Directus assignment UI should warn (not block) when an author assigns the interactive form to a passive device: "This display is set to Passive. The interactive form requires a touchscreen device. The card will be shown instead."

### 6.2 Touch Target Standards

All interactive elements: minimum 64x64px touch target, preferably 88px tall for primary navigation. Spacing between adjacent targets: minimum 16px. Text buttons have generous vertical padding (24px top/bottom). No hover-only states — everything uses tap states.

### 6.3 Navigation Model

The interactive has three levels. The visitor navigates forward by tapping; backward with a persistent back arrow; and to the home/attract screen via a home button or by idle timeout.

```
Level 0: Attract screen (idle / home)
   ↓ tap anywhere
Level 1: Exhibit overview (the card content, scrollable)
   ↓ tap "Gallery"      ↓ tap a person     ↓ tap "Related Exhibit"
Level 2a: Photo gallery  Level 2b: Person  Level 2c: Related exhibit
   (swipeable)           bio view          overview (→ Level 1 of
                                           that exhibit)
```

Back navigation: a persistent "← Back" button, top-left, 88px tall, at all Level 2 views. At Level 1, a "← Home" button returns to the attract screen.

Cross-exhibit navigation (the 3280 → Onyx 10000 link): tapping "Related Exhibit" on the 3280 navigates to Level 1 of the Onyx 10000 exhibit. The back button at Level 1 of the Onyx then returns to the 3280 Level 1. This enables the "thirty feet apart" story without leaving the kiosk app.

### 6.4 Attract Screen (Level 0)

```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│  [Hero photo — full bleed, 60% of screen height]             │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  [Exhibit title — 72px white bold, on dark overlay]          │
│                                                               │
│  [Subtitle — 32px white/80%, italic]                         │
│                                                               │
│  ┌─────────────────────────────────────────┐                 │
│  │  TAP TO EXPLORE  (96px tall button)     │                 │
│  │  48px white text, InfoAge blue fill     │                 │
│  └─────────────────────────────────────────┘                 │
│                                                               │
│  Room name — 20px white/40%, bottom-right                    │
└───────────────────────────────────────────────────────────────┘
Background: dark navy #0B1F3A
```

After 90 seconds of no interaction from any Level 1 or 2 view, the screen returns to Level 0 with a fade transition (600ms). The idle timer resets on any tap.

Before returning to Level 0, if the user is at Level 1 or deeper, show a brief countdown: "Returning to start in 10 seconds..." in a non-intrusive pill at the bottom of the screen. Tapping anywhere cancels the countdown.

### 6.5 Exhibit Overview (Level 1)

The overview is a vertically scrollable view of the exhibit's content. Touch-scroll (no scroll bars, standard iOS/Android-style momentum scrolling). Scroll position resets to top on returning to this view.

```
┌──────────────────────────────────────────────────────────────────┐
│ ← Home                                  [Exhibit title, 40px]   │
├──────────────────────────────────────────────────────────────────┤
│ [Hero image, full width, 16:9 cropped, ~400px tall]              │
│ [Caption — 20px serif italic, padding 16px]                      │
├──────────────────────────────────────────────────────────────────┤
│ INTERPRETIVE BODY                                                │
│ 26px serif, line-height 1.6, side padding 48px                   │
│ (scrollable)                                                     │
├──────────────────────────────────────────────────────────────────┤
│ THE BACKSTORY:                                                   │
│ 22px serif, line-height 1.6                                      │
├──────────────────────────────────────────────────────────────────┤
│ AT A GLANCE (bullets)                                            │
│ 24px, semi-bold                                                  │
├──────────────────────────────────────────────────────────────────┤
│ ACTION BUTTONS (3 large buttons, horizontal row, 96px tall each) │
│                                                                  │
│  [Gallery  →]    [Meet the Inventor →]   [Related Exhibit →]     │
│  (if media[])    (if people[])           (if related_assets[])   │
│                                                                  │
│  (Buttons appear only if the corresponding content exists)       │
├──────────────────────────────────────────────────────────────────┤
│ QR SECTION                                                       │
│ [QR code, 200px] "Scan to take the full story home"              │
│ 24px serif, centered                                             │
└──────────────────────────────────────────────────────────────────┘
```

If no people are linked, the "Meet the Inventor" button does not render. If no gallery items beyond the hero, "Gallery" button does not render. Buttons only appear for content that exists — Doug cannot accidentally show a blank gallery by tapping a button.

### 6.6 Photo Gallery (Level 2a)

A full-screen horizontally swipeable gallery.

```
┌──────────────────────────────────────────────────────────────┐
│ ← Back                              Photo 3 of 6             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                                                              │
│   [Full-screen photo, letterboxed within available area]     │
│   < (prev) swipe gesture or tap arrow    (next) >            │
│                                                              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ [Caption — 22px serif italic, padding 24px]                  │
│ [Source — 16px gray]   [Credit — 16px gray]                  │
└──────────────────────────────────────────────────────────────┘
```

Swipe left/right to advance photos. Left/right arrow buttons (80x80px, semi-transparent dark circles) are always visible for visitors who do not know to swipe. Dot pagination indicator (one dot per photo) is centered below the photo and above the caption.

The hero image is not repeated in the gallery — it has its own slot at the top of the Level 1 overview. The gallery shows only `asset.media[]` items.

### 6.7 Person Bio (Level 2b)

```
┌──────────────────────────────────────────────────────────────┐
│ ← Back                                                       │
├──────────────────────────────────────────────────────────────┤
│  [Portrait — 300x300px, centered, rounded or square]         │
│  [Name — 48px bold]                                          │
│  [Credentials — 28px gray]                                   │
│  [Role label — 28px italic]                                  │
│  [Lifespan — 22px gray]                                      │
├──────────────────────────────────────────────────────────────┤
│  [Full bio text — 24px serif, scrollable]                    │
└──────────────────────────────────────────────────────────────┘
```

If multiple people are linked to the asset, Level 1's "Meet the Inventor" button opens a list view first (each person shown as a 96px-tall row with thumbnail, name, and role). Tapping a person opens Level 2b for that person. The back button returns to the list, not all the way to Level 1. This is a 3-level hierarchy for multi-person exhibits; depth resets on idle.

### 6.8 Related Exhibit (Level 2c)

```
┌──────────────────────────────────────────────────────────────┐
│ ← Back to [originating exhibit name]                         │
├──────────────────────────────────────────────────────────────┤
│  RELATED EXHIBIT                                             │
│  [Connection note — 24px italic, InfoAge blue]               │
│  E.g.: "Same architect — Ken Yeager designed the MIPS R10000 │
│  that powers it. Both machines, 30 ft apart."                │
├──────────────────────────────────────────────────────────────┤
│  [Hero image of the related exhibit]                         │
│  [Related exhibit title — 48px bold]                         │
│  [Subtitle — 28px italic]                                    │
├──────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐   │
│  │  EXPLORE THIS EXHIBIT  (96px tall, InfoAge blue)      │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Tapping "Explore this exhibit" navigates to Level 1 of the related exhibit. The back stack is preserved: Back from the related exhibit's Level 1 returns to Level 2c (the connection screen), and Back from there returns to the originating Level 1. Maximum cross-exhibit traversal depth is 2 hops to prevent confusing navigation state; if the related exhibit itself has a related exhibit, that second-hop relationship is shown as a text mention only, not as a navigable button.

### 6.9 Touchscreen States

**Idle (no tap for 90s):** Countdown pill appears at 80s. At 90s, fade to attract screen.

**Loading (content fetch):** Full-screen dark navy with centered spinner (subtle, 40px) and exhibit title if known. Duration typically under 1 second on LAN.

**Gallery loading (image load):** Image area shows a shimmer placeholder; caption area is blank until the image loads.

**No content (asset unpublished or no assignment):**
Same error state as the card: "No exhibit assigned to this display" on dark navy background.

**Device class mismatch (passive device assigned interactive):**
Card or video renders as fallback. A 4-second toast at the bottom: "Interactive form not available on this display. Showing card." The toast dismisses and the card takes over.

---

## 7. Central Dashboard

The ExhibitOS dashboard is a separate React application (building on AdminApp.tsx, AdminLayout.tsx). It handles display-assignment and fleet control. Authors access it after publishing content in Directus.

### 7.1 Dashboard Navigation

The dashboard has five top-level navigation items in the left sidebar:

```
┌─────────────────┐
│  ExhibitOS      │
│  ─────────────  │
│  Overview       │
│  Rooms          │
│  Assets         │
│  Fleet          │
│  Settings       │
└─────────────────┘
```

Sidebar is 220px wide, white, border-right. Active item has InfoAge blue left border (4px) and blue text. Icon + text label for each item.

The sidebar collapses to icon-only on viewports under 1024px (for a tablet used in the museum for management). No mobile layout needed — this is a curator/admin tool on a museum workstation or tablet.

### 7.2 Overview Screen

The dashboard home. A quick-glance status surface.

```
┌────────────────────────────────────────────────────────────────┐
│  Overview                              [Date / Time]           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  SYSTEM STATUS                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Directus    │  │  4 Displays  │  │  2 Displays  │         │
│  │  Connected   │  │  Online      │  │  Offline     │         │
│  │  ● green     │  │  ● green     │  │  ● red       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                │
│  QUICK ACTIONS                                                 │
│  [Assign Exhibit]  [Export Print Card]  [Fleet Broadcast]      │
│                                                                │
│  RECENT ACTIVITY (last 5 events)                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  VCF Main Gallery · left wall — Content updated 2m ago   │  │
│  │  Fleet · pi-gallery-01 — Came online 14m ago             │  │
│  │  Asset · Concurrent 3280 — Published by Doug 1h ago      │  │
│  │  ...                                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

Directus status is a live ping from the ExhibitOS server to Directus's `/server/health` endpoint. The count tiles link to the Fleet tab filtered to online/offline.

### 7.3 Rooms Screen

The room tree is the assignment surface. Authors think in rooms, not device hostnames.

```
┌────────────────────────────────────────────────────────────────┐
│  Rooms                                          [+ Add Room]  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ▼  VCF Main Gallery                                           │
│     ┌────────────────────────────────────────────────────────┐ │
│     │  Display: Main Gallery — left wall                     │ │
│     │  Class: Passive · Platform: Pi · Form: Card            │ │
│     │  Content: The Concurrent 3280  (Published)             │ │
│     │  Status: ● Online · 2m ago                             │ │
│     │                                          [Manage →]    │ │
│     └────────────────────────────────────────────────────────┘ │
│     ┌────────────────────────────────────────────────────────┐ │
│     │  Display: Main Gallery — touchscreen kiosk             │ │
│     │  Class: Touchscreen · Platform: Pi · Form: Interactive │ │
│     │  Content: The Concurrent 3280  (Published)             │ │
│     │  Status: ● Online · 1m ago                             │ │
│     │                                          [Manage →]    │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                │
│  ▶  Lobby                                                      │
│  ▶  Server Room                                                │
└────────────────────────────────────────────────────────────────┘
```

Each room section is expandable (chevron toggle). The display card shows enough context for a curator to confirm what is playing without drilling in. The "Manage" button opens the display detail panel.

### 7.4 Display Detail (slide-in panel from right)

Clicking "Manage" on a display opens a side panel (480px wide, slides in from right, the room list dims behind it). This is the primary assignment surface.

```
┌──────────────────────────────────────────────────────────────┐
│  Main Gallery — left wall                              [✕]   │
│  Class: Passive  ·  Platform: Pi                             │
│  Room: VCF Main Gallery                                      │
├──────────────────────────────────────────────────────────────┤
│  CURRENT CONTENT                                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  The Concurrent 3280                                   │  │
│  │  Form: Card  ·  Published                              │  │
│  │  [Change Exhibit]  [Change Form]  [Remove Assignment]  │  │
│  └────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  ASSIGN NEW CONTENT                                          │
│                                                              │
│  Select exhibit:  [Search / dropdown — published only]       │
│  Form:            [Card ▼]  (Card / Video / Interactive*)    │
│                   * Interactive disabled if class = Passive  │
│                   with tooltip: "Requires touchscreen device"│
│  [Assign]                                                    │
├──────────────────────────────────────────────────────────────┤
│  PRINT CARD                                                  │
│  [Export printable card for Concurrent 3280]                 │
│  Generates a print-ready PDF via Playwright.                 │
│  [Download PDF]                                              │
├──────────────────────────────────────────────────────────────┤
│  FLEET CONTROLS                                              │
│  [Reload content]   [Reboot device]                          │
│  [Preview display]  (opens /display/<slug> in new tab)       │
├──────────────────────────────────────────────────────────────┤
│  DISPLAY PROFILE   (auto-detected + manual — see §7.4a)      │
│  Resolution 1920×1080 · Landscape · DPR 1.0   (read-only)    │
│  Physical size [43] in · Viewing distance [8] ft  [Save]     │
│  Text scale 0.89× · root rem ≈14px                           │
├──────────────────────────────────────────────────────────────┤
│  LIVE STATUS                                                 │
│  Hostname: pi-gallery-01                                     │
│  IP: 192.168.1.45   Uptime: 4d 2h   Mem free: 180 MB        │
│  Last seen: 2 min ago   Version: 1.0.3                       │
└──────────────────────────────────────────────────────────────┘
```

**Form selection interaction:** When a curator selects "Interactive" for a Passive device, the option is shown but dimmed, with a tooltip: "The interactive form requires a touchscreen device. This display is Passive and will show the card instead." This is a warning, not a hard block in the UI — the renderer enforces the gate. (A future version may hard-block at the UI layer too, but the warning is sufficient for v1 with a small, known fleet.)

**Print export interaction:**
1. Curator clicks "Download PDF."
2. Button shows "Generating..." (spinner, disabled state) while the server runs Playwright.
3. On success, browser downloads the PDF. Button returns to normal.
4. On error, button shows "Export failed — try again" in red text, stays active for retry.
5. Typical generation time: 3–8 seconds.

### 7.4a Display Profile setup (in the Display detail panel)

The Display detail panel gains a **Display Profile** section, between Fleet Controls and Live Status. It shows the auto-detected screen metrics **read-only** and lets the admin enter the two fields the browser cannot know — physical size and viewing distance — once, at provisioning.

```
┌──────────────────────────────────────────────────────────────┐
│  DISPLAY PROFILE                                            │
│  ─────────────────────────────────────────────────────────  │
│  Auto-detected  (reported by the display — read-only)        │
│   Resolution:        1920 × 1080 px      [🔄 last seen 2m ago]│
│   Orientation:       Landscape           (auto)              │
│   Pixel ratio (DPR): 1.0                                     │
│   Detected:          2026-06-01 14:22                        │
│                                                              │
│  Set by you  (the browser can't know these)                  │
│   Physical size:     [  43  ] inches (diagonal)              │
│   Viewing distance:  [   8  ] feet                           │
│   ┌────────────────────────────────────────────────────┐    │
│   │  Computed text scale: 0.89×  ·  root rem ≈ 14px      │    │
│   │  "Type will be slightly smaller than the 24-inch     │    │
│   │   desk-monitor baseline — still above the ADA floor."│    │
│   └────────────────────────────────────────────────────┘    │
│   [Save profile]                                             │
│                                                              │
│   Orientation override:  ( ) Auto  ( ) Force landscape       │
│                          ( ) Force portrait                  │
└──────────────────────────────────────────────────────────────┘
```

**Behavior:**
- **Auto-detected fields are read-only.** `Resolution`, `Orientation`, and `Pixel ratio` are populated from the display's profile report (WS agent handshake for `chromium-kiosk`; served-page probe for `fully-kiosk` — ARCHITECTURE §6a.4). A small "last seen Nm ago" with a refresh affordance shows recency; a never-reported display shows "Awaiting first report from display" and the manual fields still work.
- **Manual fields are editable** with sensible numeric inputs: `Physical size` (inches, diagonal) and `Viewing distance` (feet). Defaults are empty; while empty the system uses the baseline text-scale of 1.0 (never an error).
- **Live computed preview.** As the admin types size/distance, the panel shows the resulting **text scale** and approximate root rem (the formula in ARCHITECTURE §6a.3) with a one-line plain-language interpretation. This makes the otherwise-invisible legibility math tangible — the admin can nudge "viewing distance" up and watch type grow.
- **Orientation override.** Default `Auto` trusts the detected orientation. `Force landscape` / `Force portrait` covers a mis-reporting panel or a deliberate portrait sign on a hardware-landscape panel. The override writes `display_device.orientation` and the auto-detect stops overwriting it until set back to `Auto`.
- **Save** posts the manual fields (and any override) to the device registry; the assigned display picks up the new text-scale/orientation on its next content refresh (WS push or REST refetch). No re-provisioning.

This is an **admin/provisioning** step (Persona C, set once), not a routine curator task — it lives in the same panel but visually below the day-to-day content/print/fleet controls.

### 7.5 Assets Screen

A read-only list of published Directus assets, pulling from the ExhibitOS Directus sync cache. This screen exists so a curator can find and export a card without knowing which display it is assigned to.

```
┌────────────────────────────────────────────────────────────────┐
│  Assets                         [Search]        [Filter ▼]    │
├────────────────────────────────────────────────────────────────┤
│  Showing 3 assets  ·  3 published                              │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ [Hero thumb 80x80]  The Concurrent 3280                │    │
│  │                     Published  ·  VCF Main Gallery     │    │
│  │                     [Export Card PDF]   [View in Directus →]│
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ [Hero thumb 80x80]  SGI Onyx 10000                     │    │
│  │                     Published  ·  VCF Main Gallery     │    │
│  │                     [Export Card PDF]   [View in Directus →]│
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ [placeholder]       Wang VS 100         (Draft)        │    │
│  │                     Draft  ·  No room assigned         │    │
│  │                     (card export disabled for drafts)  │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

"View in Directus" opens Directus admin in a new tab, deep-linked to that asset record. This is the bridge that reminds curators where content editing happens. The dashboard does not replicate the asset edit form.

### 7.6 Fleet Screen

The Fleet tab is a direct evolution of the existing SignBoard fleet management pattern. It lists all registered devices with live status.

```
┌────────────────────────────────────────────────────────────────┐
│  Fleet                         [Broadcast to All]  [+ Register]│
├────────────────────────────────────────────────────────────────┤
│  [All ▼]  [Pi ▼]  [Fully Kiosk ▼]  Filter by room: [All ▼]    │
├──────────┬──────────┬──────────┬──────────┬───────────────────┤
│ Device   │ Room     │ Status   │ Last seen │ Actions           │
├──────────┼──────────┼──────────┼──────────┼───────────────────┤
│pi-gal-01 │ VCF Main │ ● Online │ 45s ago  │ [Reload][Reboot]  │
│pi-gal-02 │ VCF Main │ ● Online │ 1m ago   │ [Reload][Reboot]  │
│onn-lobby │ Lobby    │ ● Online │ 30s ago  │ [Reload][Reboot]  │
│          │          │          │          │ [Screenshot]      │
│pi-server │ Srv Room │ ○ Offline│ 4h ago   │ [Reload][Reboot]  │
├──────────┴──────────┴──────────┴──────────┴───────────────────┘
│                                                                │
│  Offline: pi-server-01  ·  Last seen: 4h ago  ·  [Dismiss]    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Per-device detail (expand row):**
Clicking a device row expands it to show:
- IP address, hostname, uptime, memory free, CPU load, software version
- Platform-specific data: Pi devices show agent version; Fully Kiosk devices show browser version and current URL
- "Off channel" warning if current URL does not match expected `/display/<slug>` — with a [Fix URL] button that issues a `loadURL` command

**Broadcast action:**
Clicking "Broadcast to All" opens a confirmation modal:
```
"Send [Reload / Reboot] to all N online devices?
This will interrupt any active visitor interaction.
[Reload All]   [Reboot All]   [Cancel]"
```
Rate limiting: after a broadcast, the button is disabled for 30 seconds to prevent accidental double-fire.

**Screenshot (Fully Kiosk only):**
Clicking "Screenshot" fetches the Fully Kiosk screenshot endpoint and displays the image in a modal. A timestamp is shown below the image. This is a diagnostic tool for confirming what a remote display is actually showing without going to the room.

**"Off channel" warning:**
If a Pi device's kiosk is displaying a URL other than its expected `/display/<slug>` (e.g. after a manual navigation during setup), the Fleet row shows an amber "Off channel" badge. A [Fix URL] button issues a `loadURL` to put it back. This pattern is carried directly from SignBoard.

### 7.7 Settings Screen

The settings screen contains the ExhibitOS-level configuration that the System Admin sets once and the curator rarely needs to touch.

- Directus connection (URL, API token, sync interval)
- `qr_base_url` — the global base for all QR codes
- Dashboard admin password change (for v1 separate-auth model)
- Card export settings (paper size, DPI — for Playwright)
- A "Test Directus connection" button that pings Directus and shows the response

---

## 8. Cross-Cutting UX Concerns

### 8.1 Accessibility

**Distance viewing (ADA museum standard):**
The primary accessibility consideration for kiosk displays is legibility at 1.0–2.0m standing distance. The size standards below are the **baseline minimums at the reference profile (24″ diagonal viewed at 5 ft)**. They are authored in `rem` and the renderer sets the CSS root rem from the profile's physical-size + viewing-distance **text-scale** (ARCHITECTURE §6a.3), so these minimums are **preserved or enlarged** on bigger/farther screens (e.g. a 75″ wall TV) and never fall below the floor (text-scale is clamped ≥ 0.85). Px values below scale proportionally with DisplayCanvas.

| Content type | Minimum size on canvas | Notes |
|---|---|---|
| Exhibit title | 64px | Bold, high contrast |
| Section headers ("AT A GLANCE") | 24px uppercase | Tracked, blue on white — confirm contrast ratio |
| Body text / backstory | 22px | Serif, line-height 1.6 |
| Bullet facts | 26–28px | Semi-bold |
| Captions | 18px | Italic, gray — acceptable for supplementary text |
| Credits | 14–16px | Low-priority; curators and close readers only |
| Touchscreen buttons | 28px text, 88px tall | Minimum touch target |
| Fleet / dashboard UI | Standard web (14–16px) | Not a distance-viewing surface |

**Color contrast:**
- All body text: minimum 4.5:1 on the card background (#FAF7F2). Confirmed for dark gray (#333) on off-white.
- Title text (white on InfoAge blue #1A3A6B): must be confirmed against the exact blue. If below 4.5:1, darken the blue to ~#14305A.
- Closer strip (white/gold on navy #0B1F3A): high contrast by design; no action needed.
- Gray caption text on off-white: the 14px credit text may fall below 4.5:1 at small size. Acceptable because credits are supplementary; confirm and document.
- Status indicators: never use color alone. Online = green dot + "Online" text. Offline = red dot + "Offline" text.

**Touch target sizes:** Covered in §6.2. Restated: minimum 64px, preferred 88px for primary actions.

**Screen reader / ARIA:**
The kiosk displays are not operated via screen reader in typical museum use; however, the dashboard is. All dashboard form fields have labels. Status colors have text labels. Error messages are announced (ARIA live regions on the fleet status and error toast components). Image alt text flows from `media_item.alt_text` into the card renderer's `<img alt>` attribute.

**No motion requirement:** No animations on the passive card renderer. Animations on the touchscreen interactive (gallery swipe, fade transitions) must respect `prefers-reduced-motion`. If set, use instant cuts instead of fades/slides.

### 8.2 Responsive Behavior by Device Class

Behavior is driven by the **Display Profile** (ARCHITECTURE §6a): card = fixed designed canvas per **orientation**, scaled-to-fit; video/touch = responsive to the actual viewport; all forms apply the profile root **text-scale**.

| Surface | Device / profile | Behavior |
|---|---|---|
| Interpretive card (landscape) | Pi/Onn + landscape 1080p monitor/TV | Landscape DisplayCanvas 1920×1080, CSS scale-to-fit; root rem from text-scale |
| Interpretive card (portrait) | Portrait-mounted panel (1080×1920) | **Portrait DisplayCanvas 1080×1920** (distinct composition, §4.2a), CSS scale-to-fit |
| Interpretive card (4K) | 3840×2160 panel, DPR 2 | Same landscape/portrait canvas, scaled up; **higher text-scale** keeps type legible at distance; QR/raster sized per DPR |
| Interpretive card (odd aspect) | Non-16:9 / ultrawide / square | Canvas scaled-to-fit with **letterbox/pillarbox** (acceptable); content never clipped |
| Video display | Pi or Onn, any orientation/resolution | **Responsive** full-screen self-hosted HTML5 `<video>`, `object-fit: contain` (no YouTube iframe on kiosks); no app-drawn bars |
| Touchscreen interactive | Pi + touchscreen, landscape **or portrait**, 1080p / 1280×800 / 4K | **Responsive fluid grid** with touch events; reflows for orientation; targets/type honor text-scale |
| Dashboard | Museum workstation (desktop) | Standard responsive layout, ≥1024px |
| Dashboard | Museum tablet (iPad/Android) | Sidebar collapses to icon-only at <1024px |
| Dashboard | Phone | Not a target; not optimized |
| Directus authoring | Any browser | Directus's own responsive layout; no customization needed |

**Portrait screens (v1, not Phase 2).** Portrait is **fully supported in v1**. `DisplayCanvas` accepts a design size (landscape `1920×1080` or portrait `1080×1920`); `RoomDisplay` picks it from `profile.orientation`. The portrait card is a distinct composition (§4.2a), not a CSS-rotated landscape. (This supersedes the earlier "Phase 2 portrait prop" note.)

**Odd aspect ratios & 4K.** The card's scale-to-fit tolerates any aspect ratio via letter/pillarboxing — never clip. On 4K (DPR 2) the canvas scales up cleanly; the profile `device_pixel_ratio` is used to request crisp QR/raster assets, and the higher physical-size/distance typically raises the text-scale so type stays legible across the gallery.

### 8.3 Empty and Error States Policy

The PRD §8 and §9a hard requirement: no demo data, no placeholder content on a live display.

| State | What shows |
|---|---|
| Display not assigned | "No exhibit assigned to this display." + room name |
| Asset is Draft (not Published) | "No exhibit assigned." (same message; do not expose draft status to a museum visitor) |
| Directus unreachable, cache fresh | Last-known-good content + subtle cache-date indicator in the closer strip |
| Directus unreachable, no cache | Error screen with reconnect message. Dark navy, no content |
| Self-hosted video missing/404 in mirror | No-content state for video display. Do not autoplay an error page |
| Related exhibit deleted | Related exhibit button does not render. No broken link |
| Gallery image fails to load | Image area shows museum's fallback image (a simple camera icon on off-white). Caption and credit still render |
| Playwright PDF export fails | Dashboard shows error toast; PDF download does not initiate; curator prompted to retry |
| Directus sync stale (>N minutes without a successful poll) | Dashboard shows a warning banner: "Content sync last succeeded [time]. Directus may be unreachable. Displays are showing cached content." |

---

## 9. Design Language Note

### 9.1 Positioning relative to SignBoard

SignBoard is an opinionated product. Its dark navy (`#0B1F3A`), gold accent (`var(--brand-gold)`), and anchor-and-wave identity are specific to Wharfside Manor — a nautical, coastal HOA. ExhibitOS forks the technical bones of SignBoard (DisplayCanvas, WebSocket fleet push, kiosk agent, Fully Kiosk REST bridge) but replaces SignBoard's visual identity entirely.

ExhibitOS has no brand identity of its own. The system's job is to present a museum's content, not to announce itself.

### 9.2 Design token defaults

The ExhibitOS default token set uses warm neutrals — not SignBoard's navy/gold. The museum deploying ExhibitOS overrides these tokens for their own palette (InfoAge, for example, provides its exact blue). The defaults ensure any museum gets a workable starting point.

| Token | Default value | Notes |
|---|---|---|
| `--exhibit-bg` | `#FAF7F2` | Warm off-white, archival paper feel |
| `--exhibit-text` | `#1A1A1A` | Near-black, high contrast |
| `--exhibit-text-secondary` | `#555555` | Captions, credits, secondary labels |
| `--exhibit-heading-color` | `#1A3A6B` | Configurable to museum house blue |
| `--exhibit-accent` | `#1A3A6B` | Section headers, borders, QR label |
| `--exhibit-card-border` | `#E0D8CC` | Warm light gray |
| `--exhibit-navy` | `#0B1F3A` | Closer strip, loading screens, error states |
| `--exhibit-gold` | `#C8A84B` | Optional accent for the closer strip; subdued, not SignBoard's vivid gold |
| `--exhibit-font-serif` | `'Georgia', serif` | Body text (replace with a real webfont: Merriweather or EB Garamond) |
| `--exhibit-font-sans` | `'Inter', sans-serif` | Headings, labels, buttons |

### 9.3 Typography rationale

Serif body text is a deliberate signal: this is a reading experience, not a dashboard. The font pairing (sans heading + serif body) mirrors print museum publications and creates the visual continuity with InfoAge's existing signs that the PRD requires. The font choices above are web-safe fallbacks; for production, embed the chosen webfonts in the Docker image (see §4.4 print note).

### 9.4 Chrome suppression

The ExhibitOS admin dashboard uses a clean, low-contrast gray-on-white scheme (inherited from SignBoard's AdminLayout). The navy left sidebar uses `#0B1F3A` as its only strong color — enough to read as "system chrome" but not enough to compete visually with exhibit content shown in the preview panel. Buttons in the dashboard are standard blue (`#1A3A6B`) or neutral gray. No gradients, no decorative backgrounds.

The display renderer has zero visible chrome in normal operation. The exhibit content is the full viewport. Status indicators (cache staleness, WebSocket connectivity) are rendered at ≤12px in low-opacity text, visible only if you look for them.

---

## 10. Open Questions Flagged to Nick

These are UX-layer items that need a decision or verification before implementation is complete.

1. **Print canvas resolution.** The PRD locked Playwright as the export pipeline but did not specify the CSS canvas size for print. A 1920x1080 canvas at 150dpi yields roughly a 12.8"x7.2" print area — smaller than InfoAge's existing signs (which appear to be ~24"x36"). Recommend increasing the CSS canvas to 3600x5400 (24"x36" at 150dpi) for the printable version while keeping 1920x1080 for on-screen. This requires a second Playwright render target (print URL vs. display URL) but is the correct approach. Confirm the target physical sign size with InfoAge before committing to the CSS dimensions.

2. **InfoAge house blue exact value.** The spec uses `#1A3A6B` as a working approximation. Nick or the dev team should match the hex against a physical InfoAge sign or their existing design files before the first print proof.

3. **Directus notification setup for the review workflow.** The authoring flow in §3.6 step 4 assumes Directus's notification system is configured to alert the Reviewer role when an asset moves to "In Review." Directus supports this natively via flows (its automation engine), but it requires setup. Confirm this is in scope for the v1 operational handoff, or simplify the workflow to email the reviewer manually.

4. **Related exhibit back-navigation cap.** The spec caps cross-exhibit traversal at 2 hops (§6.8). If the 3280 and Onyx 10000 both link to each other (bidirectional M2M relation), the visitor could loop. The 2-hop cap prevents an infinite traversal loop. Confirm this feels right from a curatorial standpoint — alternatively, the dashboard could flag bidirectional related-asset pairs and suggest adding directionality.

5. **Dashboard auth unification.** PRD §9b left this open. For v1, the spec assumes two separate logins (Directus and ExhibitOS dashboard). The "View in Directus" button in the Assets screen (§7.5) is the handoff link between the two. If a future unified SSO is implemented, the "View in Directus" deep link still works; only the login step changes.

6. **Portrait-orientation card — RESOLVED (2026-06-01): in v1.** Portrait is fully supported in v1 via a distinct designed portrait canvas (§4.2a, ARCHITECTURE §6a), not a flex-direction toggle on the landscape layout. Open verification: confirm the portrait composition reads as InfoAge house style on a real portrait sign at the first print proof (folded into the print-proof issue). The portrait canvas dimensions (`1080×1920` on-screen; print canvas TBD with InfoAge per Q1) should be confirmed against any physical portrait sign InfoAge already has.

7. **Volunteer runbook scope.** The spec describes the authoring UX. The runbook (a separate deliverable per PRD §8.2) should incorporate the exact step-by-step flows from §3.6 of this spec, formatted as a printable document. Confirm whether the runbook is within this UX spec's scope or is authored separately.

---

## 11. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-05-31 | Nick DeMarco (AI-assisted) | Initial draft. Covers Directus authoring UX, all three render targets, dashboard wireframes, accessibility, design language. |
| 0.2 | 2026-06-01 | Nick DeMarco (AI-assisted) | **Display Profile.** Added portrait card wireframe (§4.2a, 1080×1920 distinct composition); portrait now v1, not Phase 2 (resolved §10 Q6). Rewrote responsive matrix (§8.2) for portrait + odd aspect + 4K. Added Display Profile setup flow to the Display detail panel (§7.4a — auto-detected read-only fields + manual physical size/distance + live text-scale preview + orientation override). Tied §8.1 ADA minimums to the profile text-scale. Updated key-decisions table and authoring happy path. Aligns with ARCHITECTURE §6a (2026-06-01). |
