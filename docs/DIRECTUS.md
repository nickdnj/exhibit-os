# Understanding Directus — the content backbone

> **Who this is for:** anyone (museum staff included) who wants to understand *what Directus is*
> and *why ExhibitOS is built on it* — no technical background assumed. For the developer-level
> detail (the data model, sync, the API token), see [`ARCHITECTURE.md`](ARCHITECTURE.md).

## The one-sentence version

**Directus is a free, open-source program that turns a plain database into a friendly website
where non-technical people fill in forms to manage content** — and it automatically hands that
content to other apps (like ExhibitOS) through a clean data feed.

## What problem it solves for us

A museum's exhibit information — titles, photos, the story, credits, who designed it, what it
relates to — has to *live somewhere* and be *editable by volunteers*. We had two choices:

1. **Build our own content editor** (forms, logins, photo uploads, drafts, an approval step,
   edit history…). That's months of work and a maintenance burden forever.
2. **Use a proven tool that already does all of that.** That's Directus.

We chose #2. ExhibitOS doesn't reinvent the content editor — it lets Directus be the editor and
focuses on the part that's actually unique to us: **putting that content onto signs, screens, and
phones, and controlling the displays.**

## The two things Directus gives you

1. **The Data Studio** — a polished web app (you log in with a browser) where a volunteer creates
   and edits content by filling in forms. You define "collections" once — think of them as
   labeled filing cabinets: **Exhibit**, **Room**, **Person**, **Media** — and then anyone can add
   or edit entries without touching code. It includes, out of the box and at no extra cost:
   - **User accounts & roles** (e.g. an "Author" can draft, a "Curator" approves).
   - **Drafts & an approval step** so a half-finished edit never hits a live sign.
   - **Revision history** — see who changed what, and roll back.
   - **A media library** for photos and videos with captions and credits.
2. **Instant APIs** — the moment you create a collection, Directus automatically publishes a clean
   data feed of it. ExhibitOS reads that feed to render the signs. (No one at the museum ever has
   to think about this part — it's how the two programs talk.)

## What "self-hosted" means (and why it matters)

"Self-hosted" means **Directus runs on our own computer — the mini PC at the museum — not on
someone else's paid cloud service.** Practically:

- It runs as a small **Docker** container alongside ExhibitOS. No separate machine needed.
- **The museum owns its data.** It lives in a database on the mini PC. Nothing is rented, nothing
  phones home, and no vendor can raise a price or pull the plug.
- The alternative — a hosted "Directus Cloud" subscription — exists, but **we don't need it.** Same
  software, we just run it ourselves for free.

## Cost & license — the part to confirm with VCF

- **Software cost: $0.** Directus is open-source.
- **License:** the *Monospace Sustainable Core License (MSCL)*. The key term: **if your
  organization has less than $5 million in total annual income** (revenue, budget, and any funding,
  whichever is largest), **you can self-host Directus for free, in production, with no feature limits
  or paywalls.** Only organizations *over* $5M using it in production need a paid commercial license,
  and nonprofits get discounts even then.
- **VCF is a 501(c)(3) nonprofit well under that threshold**, so this is almost certainly free with
  no asterisks — we just want a quick confirmation of the income figure to document it. (Tracked as
  an open item in [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) §6.)

## What it needs to run

- **Docker** on the mini PC (the same way ExhibitOS runs).
- **A database** for Directus's content — we use **PostgreSQL** (Directus also supports MySQL,
  SQLite, and others; we picked Postgres because it handles revision history and multiple authors
  well). ExhibitOS keeps its own small SQLite database separately.
- **Modest resources** — Directus is lightweight and runs comfortably on the kind of mini PC we're
  already planning for; it does not need a powerful server.

## Where this is in the ExhibitOS build (honest status)

Directus is the **chosen and documented** content backbone, but it is **not yet wired into ExhibitOS
in the running code.** Today's working demo uses ExhibitOS's own built-in content for signs; the
Directus integration (authoring exhibits in the Data Studio → ExhibitOS rendering them) is the
**next major build phase.** This document describes the destination, and the architecture for getting
there is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Try it yourself (5 minutes, needs Docker)

You can run a throwaway Directus on your own machine to see the Data Studio:

```bash
docker run -d --name directus-test -p 8055:8055 \
  -v directus_test_db:/directus/database \
  -e SECRET="local-test-secret-change-me" \
  -e ADMIN_EMAIL="admin@example.com" \
  -e ADMIN_PASSWORD="choose-a-password" \
  -e DB_CLIENT="sqlite3" -e DB_FILENAME="/directus/database/data.db" \
  directus/directus:latest
```

Then open **http://localhost:8055** and log in with that email/password.

- ⚠️ Use a **real-looking email** (`admin@example.com`, not `admin@something.local`) — Directus
  rejects invalid TLDs at startup and the container will exit.
- Content persists in the `directus_test_db` Docker volume between runs.
- Stop / start / remove it with `docker stop directus-test` / `docker start directus-test` /
  `docker rm -f directus-test`.

To get a feel for it: **Settings → Data Model → Create Collection** (e.g. "Exhibit"), add a few
fields (Title, Status, Summary), then **Content → Exhibit → +** to author an entry. That's the exact
flow a museum volunteer would use.

## Learn more

- **Directus home & overview:** https://directus.io
- **Live demo & docs:** https://directus.io/docs
- **Source code (open-source):** https://github.com/directus/directus
- **The license, in plain terms:** https://directus.io/bsl-faq
- **How ExhibitOS uses it (developer detail):** [`ARCHITECTURE.md`](ARCHITECTURE.md) §1–3
