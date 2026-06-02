# ADR 0001 — Content source of truth: the docent wiki, not a separate CMS

**Status:** Accepted (2026-06-02) · Supersedes the "Directus as system of record" decision in PRD §9a and ARCHITECTURE.md.

## Context

ExhibitOS needs somewhere for exhibit content (titles, interpretive text, facts, media,
relationships) to live and be edited by the museum. We evaluated three options as we learned more
about the actual content and how the museum works.

What we learned mid-design changed the answer:

1. **The real collection is modest and flat.** The VCF Museum's content is ~108 artifacts, each
   essentially a title + placard text + a few facts + year + maker. Not thousands of items, not
   deeply relational. (Even with the new-space expansion: hundreds, not thousands.)
2. **The content already has a home with revision control.** The docents author placard text in the
   museum's existing **DokuWiki** ("the docents wiki"), which has built-in page revision history,
   diffs, attribution, and one-click revert. **The docents author there today and will continue to.**
3. **"We build, we don't run."** A volunteer-run museum has to operate whatever we ship. A full
   self-hosted CMS (Directus) plus its own database, service, upgrades, and license tracking is more
   moving parts than this content justifies — and it would duplicate revision control the wiki
   already provides.

## Options considered

| Option | Verdict |
|---|---|
| **Directus** (self-hosted CMS as system of record) | **Deferred.** Powerful, but heavy for a flat ~hundreds-item collection, and it duplicates the wiki's existing revision control. Kept as a future option if scale/media/multi-author needs grow. |
| **ExhibitOS owns the content** (its own exhibit model + edit/approval) | **Rejected for now.** One fewer service, but we'd rebuild light versioning the wiki already has for free. |
| **The wiki is the source; ExhibitOS ingests** | **Chosen.** Leverages the docents' existing authoring tool and its revision control; least to build and run; fits the museum's actual workflow. |

## Decision

- **The docent wiki (DokuWiki) is the system of record for exhibit narrative content and its
  revision history.** Docents author and edit there, as they do today.
- **ExhibitOS ingests** that content (via the wiki's API or periodic export) and renders it into the
  deliverable forms (interpretive card + QR, video display, touchscreen, phone deep-dive).
- **ExhibitOS owns only what the wiki does not:** which screen shows what (display assignment),
  scheduling, the device fleet, and **deliverable assets** (hero images, looping video) that aren't
  natural wiki-page content.
- **Editing Doug's content** (grammar/clarity cleanup, expansion) happens **in the wiki**, where every
  change is a tracked, attributable, revertible revision the author can review. ExhibitOS does **not**
  implement its own draft/approval/revision system.

### The split, concretely

| Lives in the wiki (authored by docents) | Lives in ExhibitOS |
|---|---|
| Title, interpretive text, key facts, people, history | Which device/room shows which exhibit; schedule |
| Revision history, diffs, attribution, revert | Hero image / video files (deliverable assets) |
| The narrative source of truth | Render layouts, the fleet, the dashboard |

## Consequences

- **To build:** a wiki-ingest path (DokuWiki XML-RPC/REST API or scheduled export) that parses page
  content into ExhibitOS's render model + local read-cache. (We have already proven the parse: the
  `the_artifacts` dump → 108 structured exhibits.)
- **Open item:** the wiki is login-gated. Ingest uses an authenticated read path; visitor "deep-dive"
  QR targets still need a *public* page (tracked in [`../OPEN-QUESTIONS.md`](../OPEN-QUESTIONS.md) §2).
- **Structured fields** the wiki doesn't hold (related-exhibit links, video URLs, hero image) are
  managed in ExhibitOS, keyed to the wiki page.
- **Preserved work:** the 108 parsed exhibits + AI-cleanup exemplars + per-deliverable gap analysis
  (exported to `data/seed/exhibits.json`) remain useful as ingest test data and as a punch-list to
  review with the docents — independent of where content ultimately lives.
- **Reversible:** if the museum later needs richer media management or many concurrent authors with
  formal roles, Directus remains a documented option ([`../DIRECTUS.md`](../DIRECTUS.md)).

## Note for readers of the older docs

PRD.md and ARCHITECTURE.md still contain the earlier Directus-centric design. Those sections are
**superseded by this ADR** for the content-source question and will be revised when the wiki-ingest
design is built out. The render/fleet/display-profile parts of the architecture are unaffected.
