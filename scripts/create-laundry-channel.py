#!/usr/bin/env python3
"""
Create (or update) a community-room channel on the SignBoard server.

Builds a channel with the "office" page set minus lightning. For slugs
beginning with "laundry", also pins the shared "Laundry Room Hours"
announcement at the top of the rotation. Idempotent: re-running with the
same slug reuses the existing channel and announcement and replaces page
assignments.

Usage:
    ./create-laundry-channel.py --slug laundry-1 --name "Laundry Room 1"
    ./create-laundry-channel.py --slug laundry-4 --name "Laundry Room 4"
    ./create-laundry-channel.py --slug gym       --name "Gym"
    ./create-laundry-channel.py --slug club-room --name "Club Room"

Auth: reads SIGNBOARD_USER and SIGNBOARD_PASS from the environment, or falls
back to --username/--password flags (default admin / wharfside2026).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


LAUNDRY_HOURS_TITLE = "Laundry Room Hours"
LAUNDRY_HOURS_BODY = (
    "Hours: 8:00 AM to 9:00 PM. "
    "Doors lock automatically at 9:00 PM — please plan your cycles accordingly."
)

# Page order for laundry channels. Page types map to the system pages that
# already exist on the server; announcement titles map to announcement pages.
LAUNDRY_PAGE_PLAN: list[dict[str, str]] = [
    {"kind": "announcement", "title": LAUNDRY_HOURS_TITLE},
    {"kind": "page_type", "page_type": "weather_current"},
    {"kind": "page_type", "page_type": "weather_hourly"},
    {"kind": "page_type", "page_type": "weather_forecast"},
    {"kind": "page_type", "page_type": "tide_current"},
    {"kind": "page_type", "page_type": "surf_report"},
    {"kind": "page_type", "page_type": "fishing_report"},
    {"kind": "announcement", "title": "Marina Project Begins This Summer "},
    {"kind": "announcement", "title": "Pool Opens May 23"},
]


USER_AGENT = "SignBoardProvision/1.0 (+local)"


def http(method: str, url: str, token: str | None = None, body: Any = None) -> Any:
    data = None
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code} {method} {url}\n{e.read().decode()}\n")
        raise


def login(base: str, user: str, password: str) -> str:
    resp = http("POST", f"{base}/api/auth/login", body={"username": user, "password": password})
    return resp["access_token"]


def find_or_create_channel(base: str, token: str, slug: str, name: str, rotation: int) -> dict:
    channels = http("GET", f"{base}/api/channels", token=token)
    for c in channels:
        if c["slug"] == slug:
            print(f"  channel '{slug}' exists (id={c['id']}) — reusing")
            if c["name"] != name or c["rotation_interval"] != rotation:
                http(
                    "PUT",
                    f"{base}/api/channels/{c['id']}",
                    token=token,
                    body={"name": name, "rotation_interval": rotation, "is_active": True},
                )
                print(f"  updated channel metadata (name/rotation)")
            return {"id": c["id"], "slug": slug, "name": name}
    created = http(
        "POST",
        f"{base}/api/channels",
        token=token,
        body={"name": name, "slug": slug, "rotation_interval": rotation},
    )
    print(f"  created channel '{slug}' (id={created['id']})")
    return created


def find_or_create_hours_page(base: str, token: str, pages: list[dict]) -> int:
    for p in pages:
        if p["page_type"] == "announcement" and p["title"] == LAUNDRY_HOURS_TITLE:
            print(f"  '{LAUNDRY_HOURS_TITLE}' exists (id={p['id']}) — ensuring body is current")
            http(
                "PUT",
                f"{base}/api/pages/{p['id']}/announcement",
                token=token,
                body={"body_text": LAUNDRY_HOURS_BODY, "priority": "normal"},
            )
            return p["id"]
    created = http(
        "POST",
        f"{base}/api/pages/announcement",
        token=token,
        body={
            "title": LAUNDRY_HOURS_TITLE,
            "body_text": LAUNDRY_HOURS_BODY,
            "priority": "normal",
        },
    )
    # New pages default to draft; flip to published so it renders in the carousel.
    http(
        "PUT",
        f"{base}/api/pages/{created['id']}",
        token=token,
        body={"is_published": True},
    )
    print(f"  created '{LAUNDRY_HOURS_TITLE}' announcement (id={created['id']}) and published")
    return created["id"]


def resolve_page_ids(pages: list[dict], hours_page_id: int | None) -> list[int]:
    by_type: dict[str, dict] = {}
    by_ann_title: dict[str, dict] = {}
    for p in pages:
        if p["page_type"] == "announcement":
            by_ann_title[p["title"]] = p
        else:
            by_type[p["page_type"]] = p

    resolved: list[int] = []
    for item in LAUNDRY_PAGE_PLAN:
        if item["kind"] == "announcement":
            if item["title"] == LAUNDRY_HOURS_TITLE:
                if hours_page_id is None:
                    continue  # not a laundry channel; skip hours page
                resolved.append(hours_page_id)
                continue
            p = by_ann_title.get(item["title"])
            if not p:
                print(f"  skip (announcement not found): {item['title']!r}")
                continue
            if not p["is_published"]:
                print(f"  skip (announcement unpublished): {item['title']!r}")
                continue
            resolved.append(p["id"])
        else:
            p = by_type.get(item["page_type"])
            if not p:
                print(f"  skip (no system page for type): {item['page_type']}")
                continue
            resolved.append(p["id"])
    return resolved


def assign_pages(base: str, token: str, channel_id: int, page_ids: list[int]) -> None:
    body = {
        "pages": [
            {"page_id": pid, "sort_order": i, "is_enabled": True}
            for i, pid in enumerate(page_ids)
        ]
    }
    http("PUT", f"{base}/api/channels/{channel_id}/pages", token=token, body=body)
    print(f"  assigned {len(page_ids)} pages (sort_order 0..{len(page_ids) - 1})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create or update a SignBoard laundry channel.")
    ap.add_argument("--slug", required=True, help="URL slug (e.g. laundry-b1)")
    ap.add_argument("--name", required=True, help="Display name (e.g. 'Laundry — Building 1')")
    ap.add_argument("--base-url", default="https://signboard.vistter.com")
    ap.add_argument("--rotation", type=int, default=30, help="Seconds per page (default 30)")
    ap.add_argument("--username", default=os.environ.get("SIGNBOARD_USER", "admin"))
    ap.add_argument("--password", default=os.environ.get("SIGNBOARD_PASS", "wharfside2026"))
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    print(f"→ {args.slug} ({args.name}) on {base}")
    token = login(base, args.username, args.password)

    ch = find_or_create_channel(base, token, args.slug, args.name, args.rotation)
    pages = http("GET", f"{base}/api/pages", token=token)
    is_laundry = args.slug.startswith("laundry")
    if is_laundry:
        hours_id = find_or_create_hours_page(base, token, pages)
        pages = http("GET", f"{base}/api/pages", token=token)  # refresh if we just created
    else:
        hours_id = None
        print("  (non-laundry channel — skipping Laundry Room Hours page)")
    page_ids = resolve_page_ids(pages, hours_id)
    if not page_ids:
        sys.stderr.write("no pages resolved — aborting\n")
        return 1
    assign_pages(base, token, ch["id"], page_ids)
    print(f"✓ display URL: {base}/display/{args.slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
