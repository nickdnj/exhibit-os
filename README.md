# ExhibitOS

**Author an exhibit once, publish it everywhere.** Museums are drowning in screens and
signs that each have to be designed, printed, and updated by hand — a problem that only
gets worse as a collection grows. ExhibitOS is a free, open-source platform that lets a
museum write the story of an artifact a single time and have it appear correctly on every
surface in the building: the interpretive card beside the case, the video display on the
wall, the touchscreen by the door, and the deep-dive page on a visitor's phone — all
controlled from one dashboard.

It is being built for, and proven at, the **Vintage Computer Federation (VCF) Museum @
InfoAge Science Center** in Wall Township, NJ — which is expanding into a new, larger space
over the next ~2 years, with hundreds of new exhibits to interpret and no scalable way to
manage what every screen shows.

---

## What it is

A small museum's storytelling is fragmented across incompatible media — a printed sign, a
video on a nearby screen, a touchscreen kiosk, a web page behind a QR code — and each is
edited independently. Correct one date and a volunteer has to find and fix it in four
places. Signs go stale, screens show the wrong thing, and the rich cross-references between
artifacts never get told.

ExhibitOS fixes this by treating it as what it really is: **a content problem, not a
hardware problem.** You model an exhibit's content once in a friendly web form, and the
system renders it many ways across cheap, ordinary screens — all managed centrally, all
runnable by volunteers without a developer in the loop.

It is **generic** — built for any museum. VCF @ InfoAge is the first deployment; "more
museums and more deliverable forms" is a design goal, not an afterthought.

## The deliverable forms

One exhibit record drives four surfaces. No content is ever duplicated.

| Form | What the visitor sees | Where |
|------|----------------------|-------|
| **Interpretive card + QR** | Title, hero photo, the story, key facts, and a QR code to go deeper. Renders on-screen **and** exports as a print-ready sign that matches the museum's existing house style. | Passive display beside the artifact / printed sign |
| **Video information display** | A self-hosted video for the artifact or the room, looped and muted, museum-appropriate. | Passive wall screen |
| **Touchscreen interactive** | Tap-through photo galleries, deeper bios, and "see also" links that jump to related exhibits. | Touch panel |
| **Central dashboard** | One admin surface to assign content to any screen, schedule it, export printable cards, and recover a frozen display — no SSH, no code. | Staff browser |

The QR on every card takes the visitor to a deep-dive page on their own phone (a web entry
with embedded video) so the story continues after they walk away.

## How it works

Content lives in **Directus** — a free, self-hosted, open-source CMS with no feature
paywall for a nonprofit. A volunteer authors an exhibit there once (with roles, drafts, and
an approval step so the live signs can't break by accident). ExhibitOS reads that content
and **renders it to every screen by device type**, caches it locally so a network blip
never blanks the gallery, and controls the physical fleet from its dashboard. The whole
stack runs in **Docker on a single mini PC**; the screens themselves are cheap — ~$20
streaming sticks, Raspberry Pis, or repurposed legacy PCs. Software cost is effectively
zero; it's MIT-licensed end to end.

## Status

🟡 **Bootstrapping.** The thinking is done and documented; the build is underway.

- ✅ PRD, technical architecture, UX spec, and development plan complete (see Documentation)
- ✅ ~40 v1 issues scoped across 9 epics in the [v1 milestone](https://github.com/nickdnj/exhibit-os/milestone/1)
- 🔨 **Pilot exhibit:** the **Concurrent 3280** end-to-end — a minicomputer designed in NJ
  whose architect, Ken Yeager, later designed the chip inside the museum's own SGI Onyx
  10000. Two machines, the same architect, thirty feet apart — exactly the kind of
  cross-reference static signage can never tell, and the proof case for ExhibitOS.

## Documentation

Start with the [docs index](docs/README.md), or jump straight in:

| Doc | What it covers |
|-----|----------------|
| [docs/README.md](docs/README.md) | Documentation index / where to start |
| [docs/VCF-PROPOSAL.md](docs/VCF-PROPOSAL.md) | **The pitch** — why ExhibitOS for the VCF Museum, and the proposed pilot |
| [docs/PRD.md](docs/PRD.md) | Product requirements — vision, the four forms, personas, scope |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture — Directus as content SoR, renderers + fleet, Display Profile, caching |
| [docs/UX-SPEC.md](docs/UX-SPEC.md) | UX specification — layouts, the InfoAge house card style, legibility |
| [docs/DEV-PLAN.md](docs/DEV-PLAN.md) | Development plan — epics, stories, and the v1 milestone |
| [docs/OPEN-QUESTIONS.md](docs/OPEN-QUESTIONS.md) | Decisions still to be made (and what we'd like museum input on) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to get involved and contribute |

## Get involved

ExhibitOS is being built in the open and welcomes collaborators — museum staff,
volunteers, and developers alike.

- **VCF / InfoAge staff:** read the [proposal](docs/VCF-PROPOSAL.md) and the
  [open questions](docs/OPEN-QUESTIONS.md) — the things we'd love your input on (your
  new-space display plan, who'd author content, where deep-dive pages should live).
- **Developers and the curious:** see [CONTRIBUTING.md](CONTRIBUTING.md), browse the
  [v1 issues](https://github.com/nickdnj/exhibit-os/milestone/1), and start a thread in
  [Discussions](https://github.com/nickdnj/exhibit-os/discussions).

## Lineage

ExhibitOS is the open information-display platform for the **Vintage Computer Federation
Museum @ InfoAge Science Center**. It began as a clean-snapshot fork of **SignBoard** — a
digital-signage system the author built and runs for a residential community on Raspberry Pi
and ~$20 streaming sticks (FastAPI + React + SQLite + WebSocket). SignBoard is good at one
thing — device-agnostic kiosk rendering and fleet control — and that is exactly the part
ExhibitOS keeps. Everything community-specific (tide, surf, and weather boards, marina
notices) is stripped out and replaced with the museum domain — exhibits, rooms, artifacts,
people, and interpretive cards — paired with Directus for content.

## License

MIT — free to use, modify, and deploy. See [LICENSE](LICENSE).
