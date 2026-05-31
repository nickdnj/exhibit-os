# ExhibitOS

**Distributed information-display infrastructure for museums.**

ExhibitOS is the central nervous system for a museum's signage: every exhibit, room,
and display piece has its own data, delivered in whatever form fits the hardware in
front of the visitor — an interpretive **card with a QR code**, a **video information
display**, or a **touchscreen interactive**. One dashboard controls every sign across
the building.

First deployment: the **Vintage Computer Federation Museum @ InfoAge Science Center**
(Wall Township, NJ — the former Camp Evans site), where Nick volunteers.

## Lineage

ExhibitOS began as **SignBoard**, a digital-signage system built for Wharfside Manor
(pool / marina / laundry-room kiosks). The core — a FastAPI + React + SQLite server
driving Raspberry Pi and streaming-stick kiosks over WebSocket, with a self-service
admin dashboard — generalizes cleanly from "community announcement boards" to
"museum exhibit infrastructure." This repo is a clean-snapshot fork of that core,
refactored for the museum domain.

## Core ideas

| Concept | What it is |
|---------|-----------|
| **Asset / Exhibit** | A physical display piece in the museum. Owns its content, in multiple deliverable forms. |
| **Room / Location** | A first-class place with one or more display devices, operating hours, and assigned content. |
| **Display device** | The screen. A *passive display* (carousel/video) or a *touchscreen* (interactive). Device-agnostic web client. |
| **Content type** | A renderable form of an asset's data: interpretive **card + QR**, **video player**, **touch-interactive**, image, text. More to come. |
| **Dashboard** | One admin surface to control every sign across every room — assign content, push updates, reboot/reload kiosks. |

## Deliverable forms (per asset)

1. **Interpretive card** — title, hero photo, interpretive text, QR code to deep content
   (a wiki entry + embedded video). Renders on-screen *and* exports as a printable card
   that matches the museum's existing sign portfolio.
2. **Video information display** — passive screen that plays embedded videos for an
   asset or room (the original SignBoard capability, generalized).
3. **Touchscreen interactive** — tap-through galleries and deeper dives on
   touch-capable hardware.

## Tech stack

FastAPI · React + Tailwind · SQLite · Docker · WebSocket · Raspberry Pi / streaming-stick kiosks

## Status

🟡 **Bootstrapping.** Seeded from SignBoard; PRD and museum-domain refactor in progress.
See [`docs/PRD.md`](docs/PRD.md).

## License

MIT
