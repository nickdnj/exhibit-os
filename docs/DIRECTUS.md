# Understanding Directus — a design option we explored and passed on

> 🔖 **Status: explored and NOT used.** Early in the design we considered standing up a self-hosted
> CMS (Directus) as ExhibitOS's content backbone. We compared it against using the museum's existing
> **docent wiki** as the content source of truth — and chose the wiki (simpler, less to run, and it
> reuses the docents' existing authoring tool and its built-in revision control). **Directus is not
> part of the ExhibitOS architecture.** For the reasoning behind the decision, see
> [`decisions/0001-content-source.md`](decisions/0001-content-source.md). This page is kept as the
> record of what was considered — and as a documented fallback if the museum ever outgrows the wiki
> (e.g. it needs richer media management or many concurrent authors with formal roles).

> **Who this is for:** anyone (museum staff included) curious about *what Directus is* and *why we
> looked at it* — no technical background assumed. Nothing here describes how ExhibitOS works today;
> for that, read [`ARCHITECTURE.md`](ARCHITECTURE.md).

## The one-sentence version

**Directus is a free, open-source program that turns a plain database into a friendly website
where non-technical people fill in forms to manage content** — and it automatically hands that
content to other apps (like ExhibitOS) through a clean data feed.

## The problem we were trying to solve

A museum's exhibit information — titles, photos, the story, credits, who designed it, what it
relates to — has to *live somewhere* and be *editable by volunteers*. When we started, that looked
like a choice between three options:

1. **Build our own content editor** (forms, logins, photo uploads, drafts, an approval step,
   edit history…). That's months of work and a maintenance burden forever.
2. **Use a proven CMS that already does all of that** — which is what Directus is.
3. **Reuse the authoring tool the docents already use** — the museum's existing DokuWiki, which
   already has revision history, diffs, and attribution.

Directus (option 2) was a strong candidate, and this page explains why. But as we learned more about
the actual collection (a flat ~hundreds-item set the docents *already* maintain in their wiki), we
chose option 3: the wiki stays the source of truth and ExhibitOS ingests it. That keeps one fewer
service to run and reuses revision control the museum already has. See
[`decisions/0001-content-source.md`](decisions/0001-content-source.md) for the full comparison. The
rest of this page describes Directus as we evaluated it.

## The two things Directus would have given us

1. **The Data Studio** — a polished web app (you log in with a browser) where a volunteer creates
   and edits content by filling in forms. You define "collections" once — think of them as
   labeled filing cabinets: **Exhibit**, **Room**, **Person**, **Media** — and then anyone can add
   or edit entries without touching code. It includes, out of the box and at no extra cost:
   - **User accounts & roles** (e.g. an "Author" can draft, a "Curator" approves).
   - **Drafts & an approval step** so a half-finished edit never hits a live sign.
   - **Revision history** — see who changed what, and roll back.
   - **A media library** for photos and videos with captions and credits.
2. **Instant APIs** — the moment you create a collection, Directus automatically publishes a clean
   data feed of it, which a renderer like ExhibitOS could read.

> The catch we eventually weighed: the docent wiki **already** provides the accounts, drafts,
> approval, and revision history in #1 — and the docents already author there. Adding Directus would
> have meant running a second authoring tool (and its database) to duplicate version control the
> museum already had. That tipped the decision to wiki-as-source.

## What "self-hosted" would have meant

Directus can run two ways: as a paid "Directus Cloud" subscription, or **self-hosted** — on your own
computer, with no cloud fees. The self-hosted path is the one we evaluated:

- It would run as a small **Docker** container alongside ExhibitOS. No separate machine needed.
- **The museum would own its data** — it lives in a database on the mini PC. Nothing rented, nothing
  phoning home, no vendor able to raise a price or pull the plug.

(Choosing the wiki as the source of truth means none of this is part of the actual deployment — the
wiki the docents already run is where content lives.)

## Cost & license (as it would have applied)

- **Software cost: $0.** Directus is open-source.
- **License:** the *Monospace Sustainable Core License (MSCL)*. The key term: **if your
  organization has less than $5 million in total annual income** (revenue, budget, and any funding,
  whichever is largest), **you can self-host Directus for free, in production, with no feature limits
  or paywalls.** Only organizations *over* $5M using it in production need a paid commercial license,
  and nonprofits get discounts even then.
- VCF is a 501(c)(3) nonprofit well under that threshold, so cost was never the blocker. The decision
  came down to **operational simplicity** — one fewer service to run — not licensing.

## What it would have needed to run

- **Docker** on the mini PC (the same way ExhibitOS runs).
- **A database** for Directus's content — typically **PostgreSQL**, which handles revision history
  and multiple authors well (Directus also supports MySQL, SQLite, and others).
- **Modest resources** — Directus is lightweight and would have run comfortably on the planned mini
  PC. Even so, it was a *second* database engine and service to operate; the wiki-ingest design keeps
  the stack to a single ExhibitOS service plus the wiki the museum already runs.

## Where this stands in the ExhibitOS build (honest status)

Directus is **not used by ExhibitOS** and never was wired into the running code. The content path
that *is* built ingests the docent wiki into a local read-cache and renders it — see
[`ARCHITECTURE.md`](ARCHITECTURE.md) for how it actually works and
[`decisions/0001-content-source.md`](decisions/0001-content-source.md) for why we chose the wiki.
This page exists only as the record of the option we explored and as a fallback to revisit if the
museum's needs ever outgrow the wiki.

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
