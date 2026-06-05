# Contributing to ExhibitOS

Thanks for your interest! ExhibitOS is an open platform for museum information
displays, being built first for the **Vintage Computer Federation Museum @ InfoAge**.
Collaborators come in two flavors and **both are welcome**:

- **Museum people** — curators, docents, managers, exhibit designers. You don't need to
  write code to shape this. The most valuable contributions right now are answering the
  questions in [`docs/OPEN-QUESTIONS.md`](docs/OPEN-QUESTIONS.md) about how a real museum
  works, what hardware the space will have, and how content should be authored.
- **Developers / makers** — full-stack web (FastAPI + React), Raspberry Pi / kiosk tinkerers, and
  anyone who has wrangled DokuWiki exports or APIs.

## Where to start

1. Read the [README](README.md) for the vision, then the **docs index**
   ([`docs/README.md`](docs/README.md)) for a guided reading order.
2. If you're with VCF or another museum: read the
   [VCF Proposal](docs/VCF-PROPOSAL.md) and weigh in on
   [Open Questions](docs/OPEN-QUESTIONS.md).
3. If you want to build: the [Dev Plan](docs/DEV-PLAN.md) breaks v1 into epics and stories,
   tracked as [GitHub issues](https://github.com/nickdnj/exhibit-os/issues) on the
   **v1 milestone**.

## How to collaborate

- **Discuss ideas, ask questions, or weigh in on open questions:** open a
  [GitHub Discussion](https://github.com/nickdnj/exhibit-os/discussions) — no code required.
- **Report a bug or pick up scoped work:** open or comment on an
  [Issue](https://github.com/nickdnj/exhibit-os/issues). Issues that need museum/VCF input
  carry the `vcf-input` label.
- **Contribute code:** fork, branch, and open a pull request that references the issue it
  addresses (e.g. `Closes #12`). Keep PRs focused; match the surrounding code style.

## Design-first

ExhibitOS is documented before it's built. If a change affects the data model, the render
targets, the fleet, or the museum-facing experience, please note it against the relevant doc
in `docs/` (or flag it in a Discussion) so the design and the code stay in sync.

## Guiding principles

- **Author once, publish everywhere** — one exhibit record drives every display form.
- **Free and runnable by volunteers** — no vendor lock-in, no per-screen fees; museum staff
  must be able to own and operate it without the original developer.
- **Never show fake content to a visitor** — when something's missing or offline, show a clean
  empty/last-known-good state, never demo data.

## License

By contributing, you agree your contributions are licensed under the project's
[MIT License](LICENSE).
