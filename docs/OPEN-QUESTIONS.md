# Open Questions

ExhibitOS is being designed in the open. This page is the single place to see **what's
decided** and **what's still open** — especially the things we need **VCF / museum input** on.

> 💬 **Want to weigh in?** Open a [Discussion](https://github.com/nickdnj/exhibit-os/discussions)
> or comment on an [Issue](https://github.com/nickdnj/exhibit-os/issues) tagged `vcf-input`.
> You do **not** need to be a developer to help with the questions below — most of them are
> about how a real museum works.

---

## ✅ Decisions already locked

These are settled (see [`PRD.md`](PRD.md) §9 and [`ARCHITECTURE.md`](ARCHITECTURE.md) for rationale):

- **Content lives in the museum's docent wiki** (where docents already author, with built-in revision control); ExhibitOS **ingests** and renders it. A self-hosted CMS was explored and passed on — see [`decisions/0001-content-source.md`](decisions/0001-content-source.md).
- **One deployment per museum** — fully isolated; "generic platform" means anyone can deploy the same code.
- **Kiosk video is self-hosted HTML5** (no YouTube embedded on a public kiosk — escape risk); YouTube is for the phone/QR deep-dive only. Kiosk browsers are locked to the ExhibitOS origin.
- **Interpretive cards render on-screen and export to print** (Playwright), matching InfoAge's existing sign style — in **both landscape and portrait**.
- **Every display has a Profile** (platform, resolution, orientation, physical size, viewing distance) that auto-adapts the layout and text size to that screen.
- **Printable-card engine, QR scheme, caching, tenancy** — resolved (PRD §9a).

---

## ❓ Open — needs VCF / museum input

These shape the build and are the best places to collaborate.

### 1. The new space & hardware
- What displays will the new building have — sizes, **orientation (landscape vs portrait)**, touch vs passive, and platform (smart TVs / streaming sticks / Pis / repurposed PCs)?
- What's the network situation (one LAN? where would the small always-on server live)?
- Any displays or screens you already own that we should plan around?

### 2. Deep-content (phone) pages
- When a visitor scans a QR for the "full story," where should that page live? The VCF wiki
  (vcfed.org/wiki) turns out to be a **gated docents wiki** (login required) — so a public,
  visitor-readable target is needed. Options: ExhibitOS hosts the public deep page, or VCF opens
  a public wiki section. **Which do you prefer?**

### 3. Look & house style
- ExhibitOS cards should match InfoAge's existing ~9-sign portfolio. We need the physical **sign
  dimensions** (landscape *and* portrait) and the exact **house "blue"** (or design files) for a
  faithful print proof.

### 4. Content & curation
- Docents already author placard text in the wiki. Which pages/namespace should ExhibitOS ingest, and who curates that set?
- Which exhibits are highest priority for the new space?

### 5. Operations & sustainability ("we build, we don't run")
- ExhibitOS is built so **museum staff own and operate it** — not the original developer. Who at
  VCF would own the day-to-day (adding exhibits, managing displays) once it's stood up? This shapes
  how much we automate and what the runbook must cover.

### 6. Wiki access for ingest
- ExhibitOS needs a read path into the docent wiki (DokuWiki) to ingest exhibit content. v1 ingests a
  DokuWiki **export file**; the next step is the **live DokuWiki API** (XML-RPC/REST) with a read-only
  docent account, or a scheduled export. Need to confirm the wiki's API is enabled and agree on an
  access method.

---

## 🔧 Open — engineering / internal

Lower-stakes, resolved during build:

- **Print canvas dimensions per orientation** — set once the physical sign sizes (Q3) are known.
- **Content review** — handled by the docent wiki's own revision history/diffs/attribution; ExhibitOS does not implement its own review step.
- **Text-scale defaults** — baseline 24″ @ 5 ft; per-display physical size/distance entered by an admin once.
- **Device attribution** — each kiosk URL carries a `?device_id=` so a screen can report its profile.

---

*Pilot focus: the **Concurrent 3280** exhibit end-to-end, as living proof before any
building-wide commitment. See [`VCF-PROPOSAL.md`](VCF-PROPOSAL.md).*
