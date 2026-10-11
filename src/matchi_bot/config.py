from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

import yaml

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass
class TimeWindow:
    weekdays: list[int] = field(default_factory=lambda: list(range(7)))
    time_from: time = time(0, 0)
    time_to: time = time(23, 59)

    def matches(self, start, end) -> bool:
        """True if the slot lies entirely within this window on a wanted weekday."""
        if start.weekday() not in self.weekdays:
            return False
        end_time = end.time() if end.date() == start.date() else time(23, 59)
        return self.time_from <= start.time() and end_time <= self.time_to


@dataclass
class FacilityConfig:
    slug: str
    sport: int
    windows: list[TimeWindow] = field(default_factory=lambda: [TimeWindow()])

    def matches(self, start, end) -> bool:
        return any(w.matches(start, end) for w in self.windows)


@dataclass
class Config:
    days_ahead: int
    facilities: list[FacilityConfig]


def _parse_time(value: str) -> time:
    hours, minutes = str(value).split(":")
    hours, minutes = int(hours), int(minutes)
    return time(23, 59) if hours == 24 else time(hours, minutes)


def _parse_window(entry: dict) -> TimeWindow:
    window = TimeWindow()
    if "weekdays" in entry:
        try:
            window.weekdays = [WEEKDAYS.index(str(d).lower()[:3]) for d in entry["weekdays"]]
        except ValueError:
            raise ValueError(f"Invalid weekday in {entry['weekdays']}, use {WEEKDAYS}")
    if "time_from" in entry:
        window.time_from = _parse_time(entry["time_from"])
    if "time_to" in entry:
        window.time_to = _parse_time(entry["time_to"])
    return window


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    facilities = []
    slugs = set()
    for entry in raw.get("facilities") or []:
        if "slug" not in entry or "sport" not in entry:
            raise ValueError(f"Facility entry needs 'slug' and 'sport': {entry}")
        slug = str(entry["slug"])
        if slug in slugs:
            raise ValueError(f"Facility '{slug}' is listed twice, use 'windows' for several time windows")
        slugs.add(slug)
        # Either a list of windows, or a single window given directly on the facility.
        windows = [_parse_window(w) for w in entry["windows"]] if "windows" in entry else [_parse_window(entry)]
        facilities.append(FacilityConfig(slug=slug, sport=int(entry["sport"]), windows=windows))
    if not facilities:
        raise ValueError("config.yaml has no facilities")
    return Config(days_ahead=int(raw.get("days_ahead", 7)), facilities=facilities)
