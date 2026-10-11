"""Persistent state, stored as JSON and committed back to the repo by the workflow.

Shape:
{
  "facilities": {"<slug>": {"id": "2311", "name": "A6 GK Padel"}},
  "slots": {"<slug>": {"2026-10-13": ["Padel 1|2026-10-13T18:00:00+02:00", ...]}},
  "last_error_alert": "2026-10-11T12:00:00+00:00"
}
"""
import json
from pathlib import Path


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def find_new_slots(previous: dict[str, list[str]] | None, current: dict[str, list]) -> list:
    """Return slots in `current` that were not free last time.

    `previous` maps date -> slot keys, `current` maps date -> Slot objects.
    Dates we have never seen before (first run, new facility, a day entering
    the window) are treated as a baseline and never produce notifications.
    """
    if not previous:
        return []
    new = []
    for day, slots in current.items():
        if day not in previous:
            continue
        seen = set(previous[day])
        new.extend(slot for slot in slots if slot.key not in seen)
    return new
