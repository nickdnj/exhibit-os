# ExhibitOS for the VCF Museum @ InfoAge

**A free, open-source way to author an exhibit once and publish it to every screen and sign
in the building — built by one of your own docents, designed for volunteers to own.**

---

## The opportunity

The VCF Museum is expanding into a new, larger space over the next ~2 years. That space is
currently empty and needs a full build-out — which means **hundreds of new exhibits to
interpret**, each needing a sign, and many deserving more: a video, an interactive, a place
for a curious visitor to go deeper.

That's a wonderful problem to have. It's also a content problem at a scale the museum has
never had to manage all at once. The question isn't just "what do we put on the wall?" —
it's "how does a small volunteer team produce, update, and keep consistent the
interpretation for hundreds of artifacts, across multiple kinds of displays, for years?"

ExhibitOS exists to answer that question.

## Why status-quo signage falls short

Printed signage has served the museum well, but it doesn't scale to what's coming:

- **Every sign is a one-off.** Each is designed individually in a layout tool, then frozen.
  There is no shared source for the title, photo, credits, and backstory.
- **Updates are slow and costly.** Correct a date or swap a photo and someone re-designs,
  re-prints, and re-mounts the sign. Multiply that by hundreds of exhibits.
- **There's no central control.** Nothing lets staff see — let alone manage — what every
  screen in the building is showing right now.
- **It doesn't tell the deep stories.** A static sign can't hold a video, a photo gallery,
  or a "see also" link to the related artifact across the room. The richest connections in
  the collection go untold because no single tool knows about both objects.
- **It doesn't scale to volunteers.** Sustaining hundreds of frozen signs by hand is more
  than a volunteer team can carry over a two-year build-out.

## The ExhibitOS solution

**Author once, publish everywhere.** A volunteer writes the story of an artifact a single
time, in a friendly web form. From that one record ExhibitOS produces:

- the **on-screen interpretive card** beside the artifact — *and* a **print-ready sign that
  matches your existing house style** (ENIAC / UNIVAC / Wang signs), so digital and printed
  exhibits look like one coherent museum;
- a **video information display** for the artifact or the whole room;
- a **touchscreen interactive** with photo galleries, fuller bios, and links to related
  exhibits;
- a **QR code** on every card that sends visitors to a deep-dive page on their own phone,
  so the story continues after they leave.

Correct a date once and **every surface updates**. And it's all managed from **one
dashboard** — assign content to any screen, schedule it, export a printable sign, or
recover a frozen display, without touching code or calling a developer.

## Why it fits VCF

- **Free and open-source (MIT).** No license fees, ever. The museum can use it, modify it,
  and keep it forever.
- **No per-screen SaaS fees, no vendor lock-in.** Content lives in **Directus**, a free
  self-hosted CMS with no feature paywall for a nonprofit your size. Nothing about this
  arrangement can be taken away or priced up later.
- **Cheap, ordinary hardware.** The whole system runs in Docker on **one mini PC**. Screens
  are inexpensive — ~$20 streaming sticks, Raspberry Pis, or even repurposed legacy PCs
  (fittingly, for a computer museum).
- **Volunteer-runnable by design.** Authoring, approval, display assignment, and even
  recovering a frozen screen are all self-service web tasks. This is a first-class
  requirement, not a hope: a non-technical volunteer, given only a short runbook, should be
  able to add an exhibit and put it on a screen start to finish.
- **Built by one of your own.** It's being developed by the Concurrent 3280's docent, for
  this museum first — not adapted from a generic product that doesn't understand museums.

## Proposed pilot: the Concurrent 3280, end-to-end

Before any building-wide commitment, let's prove it with **one real exhibit on one or two
displays**: the **Concurrent 3280** minicomputer.

It's the ideal proof case. The 3280 was designed in New Jersey, and its architect, **Ken
Yeager**, later designed the chip inside the museum's own **SGI Onyx 10000** — two machines,
the same architect, **thirty feet apart**. That's exactly the kind of cross-reference a
static sign can never tell and an ExhibitOS exhibit tells naturally, with a "see also" link
that ties the gallery together.

The pilot would deliver the full picture in miniature:

- the 3280 authored once in Directus;
- its **printed sign matching your existing house style**, reviewed side-by-side with your
  current signs before anything goes on a wall;
- the on-screen card, a video display, and a touchscreen interactive, all from that one
  record;
- the QR deep-dive on a phone;
- the whole thing managed from the dashboard — and handed off so a volunteer can edit it.

If the pilot earns your confidence, it scales to the new space exhibit by exhibit.

## What we'd need from VCF to go further

Framed as a conversation, not a list of demands — these are the things that would let us
plan well together:

- **A look at the new-space display and hardware plan** — what kinds of screens are
  envisioned, and roughly how many, so we can recommend cheap, compatible options.
- **Network basics for the new space** — is there Wi-Fi / wired networking the displays and
  mini PC can share?
- **Who would author and curate content** — which volunteers, and how you'd want the
  review/approval step to work.
- **Where deep-content (phone) pages should live** — your own wiki, a museum page, or
  somewhere we host. ExhibitOS points the QR wherever you prefer.

## Cost reality

- **Software: ≈ $0.** MIT-licensed; Directus free self-hosted tier; Docker on hardware you
  likely already have or can repurpose.
- **Hardware: ≈ $20–50 per screen** (streaming stick, Raspberry Pi, or repurposed PC), plus
  the displays themselves.
- **The real cost is content authoring effort** — writing and curating the interpretation
  for each exhibit. That cost exists no matter what tool you use; **ExhibitOS is built
  specifically to make it manageable** by removing the per-sign design-and-reprint overhead
  and letting volunteers do it themselves.

## Next steps

1. **A short look at the pilot.** Let's review the Concurrent 3280 exhibit together — the
   printed sign beside your existing ones, and the on-screen forms — and see if it feels
   right.
2. **A conversation about the new space.** Share the display/hardware thinking when it's
   ready; we'll map out what an ExhibitOS rollout could look like.
3. **No commitment required to start.** The pilot stands on its own as a working exhibit.
   Building-wide adoption is a later, separate decision — made only once you've seen it work.

*Questions, or want to dig into the technical side? The full
[product requirements](PRD.md), [architecture](ARCHITECTURE.md), and
[open questions](OPEN-QUESTIONS.md) are in this repository, and we're glad to walk through
any of it.*
