"""Wiki-ingest service — DokuWiki export -> ExhibitOS Exhibit rows.

The docent wiki (DokuWiki) is the system of record for exhibit narrative
content (ADR-0001). This service parses a DokuWiki export and upserts the
parsed exhibits into the local read-cache (the `exhibits` table), keyed by a
url-safe slug derived from the title.

Re-ingest is idempotent: the wiki-sourced fields are only refreshed when the
parsed content_hash changes, and the ExhibitOS-owned display fields
(hero_image / video_url / deep_content_url / location) are NEVER overwritten.

For now the input is a static export FILE; later it will be the live DokuWiki
API feeding the same `parse_dokuwiki()` parser.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime

from ..database import get_session
from ..models.exhibit import Exhibit

DEFAULT_EXPORT_PATH = "data/wiki-export/the_artifacts.txt"

# A heading line: capture the leading run of '=', the text, and the trailing run.
_HEADING_RE = re.compile(r"^(=+)\s*(.*?)\s*(=+)\s*$")
# A DokuWiki bullet: two-or-more leading spaces then '*'.
_BULLET_RE = re.compile(r"^\s{2,}\*\s?(.*)$")
# Year tokens in the body.
_YEAR_RE = re.compile(r"\b(1[6-9]\d{2}|20[0-1]\d)\b")
_YEAR_MIN, _YEAR_MAX = 1640, 2010


def _slugify(title: str) -> str:
    """Derive a url-safe, stable slug from an exhibit title."""
    # Drop a trailing "~1622" / "1945"-style date suffix noise from the slug source
    # but keep enough of the title to stay unique. We just normalize aggressively.
    s = title.lower()
    # Replace anything that isn't a-z 0-9 with a hyphen
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "exhibit"


def _clean_inline(text: str) -> str:
    """Strip DokuWiki inline markup (** bold, // italic)."""
    text = text.replace("**", "")
    text = text.replace("//", "")
    return text


def _is_subsection_marker(delim_len: int) -> bool:
    """Level-3 (and the stray level-4) markers are dropped, keeping their text."""
    return delim_len in (3, 4)


def _split_exhibits(text: str) -> list[tuple[str, list[str]]]:
    """Split the export into (title, body_lines) pairs.

    An exhibit title is a heading line whose BOTH delimiters are exactly length 5.
    Everything between two level-5 headings is the preceding exhibit's body.
    """
    exhibits: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            left, htext, right = m.group(1), m.group(2), m.group(3)
            if len(left) == 5 and len(right) == 5:
                # Start of a new exhibit — flush the previous one.
                if current_title is not None:
                    exhibits.append((current_title, current_body))
                current_title = htext.strip()
                current_body = []
                continue
            if _is_subsection_marker(len(left)) or _is_subsection_marker(len(right)):
                # Subsection marker line (e.g. "=== Placard Text ===") — drop it.
                continue
            # Any other heading (e.g. the level-6 page title) — skip if no exhibit
            # is open; otherwise treat as plain body text (rare).
            if current_title is None:
                continue
        if current_title is not None:
            current_body.append(line)

    if current_title is not None:
        exhibits.append((current_title, current_body))

    return exhibits


def _extract_year(body_text: str, title: str) -> int | None:
    """Earliest in-range 4-digit year in the body, else in the title."""
    def earliest_in_range(s: str) -> int | None:
        years = [int(y) for y in _YEAR_RE.findall(s)]
        years = [y for y in years if _YEAR_MIN <= y <= _YEAR_MAX]
        return min(years) if years else None

    return earliest_in_range(body_text) or earliest_in_range(title)


def _parse_body(body_lines: list[str]) -> tuple[str, list[str]]:
    """Separate narrative paragraphs from bullet key-facts.

    Returns (body_text, key_facts). Bullets become plain fact strings;
    everything else is interpretive narrative, blank-line-collapsed.
    """
    narrative: list[str] = []
    facts: list[str] = []

    for raw in body_lines:
        bullet = _BULLET_RE.match(raw)
        if bullet:
            fact = _clean_inline(bullet.group(1)).strip()
            if fact:
                facts.append(fact)
            continue
        narrative.append(_clean_inline(raw).rstrip())

    # Collapse runs of blank lines and trim.
    text_lines: list[str] = []
    prev_blank = False
    for ln in narrative:
        is_blank = not ln.strip()
        if is_blank and prev_blank:
            continue
        text_lines.append(ln)
        prev_blank = is_blank
    body_text = "\n".join(text_lines).strip()

    return body_text, facts


def parse_dokuwiki(text: str) -> list[dict]:
    """Parse a DokuWiki export into a list of structured exhibit dicts.

    Each dict: title, body_text, key_facts (list[str]), people, year, related,
    source_ref.
    """
    results: list[dict] = []
    seen_slugs: dict[str, int] = {}
    for title, body_lines in _split_exhibits(text):
        if not title:
            continue
        body_text, facts = _parse_body(body_lines)
        base_slug = _slugify(title)
        # Disambiguate identically-titled exhibits with a stable numeric suffix
        # (-2, -3, ...) in document order so slugs stay unique and reproducible.
        count = seen_slugs.get(base_slug, 0) + 1
        seen_slugs[base_slug] = count
        slug = base_slug if count == 1 else f"{base_slug}-{count}"
        year = _extract_year(body_text, title)

        results.append(
            {
                "title": title,
                "slug": slug,
                "body_text": body_text,
                "key_facts": facts,
                "people": None,  # no reliable structured people field in this export
                "year": year,
                "related": None,  # related-exhibit links are ExhibitOS-managed (ADR-0001)
                "source_ref": f"the_artifacts#{slug}",
            }
        )
    return results


def _content_hash(parsed: dict) -> str:
    """Stable hash over the wiki-sourced fields only."""
    payload = "".join(
        [
            parsed["title"],
            parsed["body_text"],
            "\n".join(parsed["key_facts"]),
            parsed.get("people") or "",
            str(parsed.get("year") or ""),
            parsed.get("related") or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ingest_from_file(path: str | None = None) -> dict:
    """Parse the export at `path` and upsert exhibits by slug.

    Wiki-sourced fields are refreshed only when content_hash changed.
    ExhibitOS-owned fields are never touched. Idempotent.

    Returns counts: {created, updated, unchanged, total}.
    """
    resolved = path or os.environ.get("WIKI_EXPORT_PATH") or DEFAULT_EXPORT_PATH
    with open(resolved, "r", encoding="utf-8") as f:
        text = f.read()

    parsed_list = parse_dokuwiki(text)

    created = updated = unchanged = 0
    now = datetime.utcnow()

    with get_session() as db:
        for parsed in parsed_list:
            key_facts = "\n".join(parsed["key_facts"])
            content_hash = _content_hash(parsed)

            existing = db.query(Exhibit).filter(Exhibit.slug == parsed["slug"]).first()
            if existing is None:
                db.add(
                    Exhibit(
                        slug=parsed["slug"],
                        title=parsed["title"],
                        year_introduced=parsed["year"],
                        body_text=parsed["body_text"],
                        key_facts=key_facts,
                        people=parsed["people"],
                        related_exhibits=parsed["related"],
                        source_ref=parsed["source_ref"],
                        content_hash=content_hash,
                        ingested_at=now,
                    )
                )
                created += 1
            elif existing.content_hash != content_hash:
                # Refresh wiki-sourced fields ONLY. Never touch ExhibitOS-owned fields.
                existing.title = parsed["title"]
                existing.year_introduced = parsed["year"]
                existing.body_text = parsed["body_text"]
                existing.key_facts = key_facts
                existing.people = parsed["people"]
                existing.related_exhibits = parsed["related"]
                existing.source_ref = parsed["source_ref"]
                existing.content_hash = content_hash
                existing.ingested_at = now
                updated += 1
            else:
                unchanged += 1

        db.commit()

    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "total": len(parsed_list),
    }
