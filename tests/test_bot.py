from datetime import datetime, time, timedelta
from pathlib import Path

import pytest

from matchi_bot.config import FacilityConfig, TimeWindow, load_config
from matchi_bot.matchi import TZ, MatchiFormatError, Slot, parse_slots
from matchi_bot.state import find_new_slots

FIXTURE = Path(__file__).parent / "fixtures" / "listslots.html"


def make_slot(court: str, hour: int) -> Slot:
    start = datetime(2026, 10, 13, hour, tzinfo=TZ)
    return Slot(court, start, start.replace(hour=hour + 1), f"id-{court}-{hour}", "https://example")


def test_parse_slots_from_fixture():
    slots = parse_slots(FIXTURE.read_text(encoding="utf-8"))
    assert len(slots) == 34
    first = slots[0]
    assert first.court == "Padel 1"
    assert first.start == datetime(2026, 10, 13, 6, 0, tzinfo=TZ)
    assert first.end == datetime(2026, 10, 13, 7, 0, tzinfo=TZ)
    assert first.slot_id == "41ea854d-3872-4b68-a1b7-5d014b7bc7d2"
    assert first.booking_url.startswith("https://www.matchi.se/login/auth?returnUrl=")


def test_parse_empty_fragment():
    assert parse_slots("<div>No available time slots</div>") == []


def test_parse_detects_format_change():
    with pytest.raises(MatchiFormatError):
        parse_slots('<button class="btn btn-slot">18</button>')


def test_first_run_is_baseline():
    assert find_new_slots(None, {"2026-10-13": [make_slot("Padel 1", 18)]}) == []


def test_new_slot_is_reported():
    a, b = make_slot("Padel 1", 18), make_slot("Padel 2", 18)
    previous = {"2026-10-13": [a.key]}
    assert find_new_slots(previous, {"2026-10-13": [a, b]}) == [b]


def test_removed_slot_is_not_reported():
    a, b = make_slot("Padel 1", 18), make_slot("Padel 2", 18)
    previous = {"2026-10-13": [a.key, b.key]}
    assert find_new_slots(previous, {"2026-10-13": [a]}) == []


def test_new_day_in_window_is_baseline():
    previous = {"2026-10-12": []}
    assert find_new_slots(previous, {"2026-10-13": [make_slot("Padel 1", 18)]}) == []


def test_facility_filter():
    weekend = TimeWindow(weekdays=[5, 6], time_from=time(8), time_to=time(19))
    weekday = TimeWindow(weekdays=[0, 1, 2, 3, 4], time_from=time(18), time_to=time(20))
    fc = FacilityConfig(slug="x", sport=1, windows=[weekend, weekday])

    def at(day, hour, minutes=60):
        start = datetime(2026, 10, day, hour, tzinfo=TZ)
        return start, start + timedelta(minutes=minutes)

    assert fc.matches(*at(13, 18))  # Tuesday 18-19
    assert fc.matches(*at(13, 19))  # Tuesday 19-20
    assert not fc.matches(*at(13, 20))  # Tuesday 20-21, ends after window
    assert not fc.matches(*at(13, 17))  # Tuesday 17-18, too early
    assert fc.matches(*at(17, 8))  # Saturday 08-09
    assert fc.matches(*at(18, 18))  # Sunday 18-19
    assert not fc.matches(*at(18, 18, 90))  # Sunday 18-19:30, ends after window


def test_load_config_with_windows(tmp_path):
    (tmp_path / "config.yaml").write_text(
        Path(__file__).parent.parent.joinpath("config.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    config = load_config(tmp_path / "config.yaml")
    assert [f.slug for f in config.facilities] == ["hellastk", "solnatenniscenter"]
    assert all(len(f.windows) == 2 and f.sport == 1 for f in config.facilities)
