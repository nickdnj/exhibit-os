#!/usr/bin/env python3
"""Ingest exhibit content from the docent-wiki export into ExhibitOS.

Run inside the venv from the repo root, either as a module or a script:

    python -m scripts.ingest_wiki
    python scripts/ingest_wiki.py

Input path comes from $WIKI_EXPORT_PATH, defaulting to
data/wiki-export/the_artifacts.txt. Prints upsert counts.
"""
import os
import sys

# Make `server` importable when run as a plain script (python scripts/ingest_wiki.py).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.database import engine  # noqa: E402
from server.models.base import Base  # noqa: E402
import server.models  # noqa: E402,F401  (registers Exhibit on Base.metadata)
from server.services.wiki_ingest import ingest_from_file  # noqa: E402


def main() -> int:
    # Ensure tables exist when ingest runs standalone (no app lifespan).
    Base.metadata.create_all(bind=engine)

    counts = ingest_from_file()
    print(
        "Wiki ingest complete: "
        f"{counts['created']} created, "
        f"{counts['updated']} updated, "
        f"{counts['unchanged']} unchanged "
        f"({counts['total']} parsed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
