"""Admin settings API — backs the Settings page."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from .auth import get_current_user
from ..services.settings_service import (
    settings_service, SETTING_REGISTRY,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])

MASK = "••••••••"


class SettingItem(BaseModel):
    key: str
    group: str
    value_type: str
    label: str
    description: Optional[str] = None
    options: Optional[str] = None
    value: str
    is_secret: bool = False
    is_readonly: bool = False
    sort_order: int = 0


class SettingUpdate(BaseModel):
    key: str
    value: str


class SettingsBulkUpdate(BaseModel):
    updates: list[SettingUpdate]


def _masked_item(entry: dict, value: str) -> SettingItem:
    """Apply masking and presentation rules to a raw registry+value pair."""
    is_secret = entry.get("is_secret", False)
    display_value = value
    if is_secret and value:
        display_value = MASK
    return SettingItem(
        key=entry["key"],
        group=entry["group"],
        value_type=entry["value_type"],
        label=entry["label"],
        description=entry.get("description"),
        options=entry.get("options"),
        value=display_value,
        is_secret=is_secret,
        is_readonly=entry.get("is_readonly", False),
        sort_order=entry.get("sort_order", 0),
    )


@router.get("", response_model=list[SettingItem])
def list_settings(_user=Depends(get_current_user)):
    """Return all registered settings grouped for the UI. Secrets masked."""
    items = []
    for entry in SETTING_REGISTRY:
        value = settings_service.get(entry["key"])
        items.append(_masked_item(entry, value))
    items.sort(key=lambda s: (s.group, s.sort_order, s.label))
    return items


@router.patch("")
def update_settings(body: SettingsBulkUpdate, _user=Depends(get_current_user)):
    """Update a subset of settings. Masked values in the payload are ignored
    (prevents accidental overwrite of a secret with the mask string)."""
    known = {e["key"]: e for e in SETTING_REGISTRY}
    applied = 0
    skipped_mask: list[str] = []
    unknown: list[str] = []

    for upd in body.updates:
        entry = known.get(upd.key)
        if entry is None:
            unknown.append(upd.key)
            continue
        if entry.get("is_readonly"):
            continue
        # Don't clobber real secret with the display mask when user didn't retype
        if entry.get("is_secret") and upd.value == MASK:
            skipped_mask.append(upd.key)
            continue
        settings_service.set(upd.key, upd.value)
        applied += 1

    if unknown:
        raise HTTPException(
            status_code=400,
            detail={"message": "Unknown setting key(s)", "keys": unknown},
        )

    return {
        "applied": applied,
        "skipped_unchanged_secret": skipped_mask,
    }
