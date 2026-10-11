"""Run one check: fetch free slots, diff against state, notify via Telegram, save state."""
import html
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import matchi, telegram
from .config import load_config
from .state import find_new_slots, load_state, save_state

ROOT = Path(os.environ.get("MATCHI_BOT_ROOT", Path.cwd()))
ERROR_ALERT_INTERVAL = timedelta(hours=24)
WEEKDAY_SV = ["mån", "tis", "ons", "tor", "fre", "lör", "sön"]
MONTH_SV = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]


def notify(text: str) -> None:
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set, would have sent:\n" + text)
        return
    telegram.send_message(token, chat_id, text)


def format_slot(slot: matchi.Slot) -> str:
    s = slot.start
    when = f"{WEEKDAY_SV[s.weekday()]} {s.day} {MONTH_SV[s.month - 1]} {s:%H:%M}–{slot.end:%H:%M}"
    return f"• {when} · {html.escape(slot.court)} · <a href=\"{html.escape(slot.booking_url)}\">Boka</a>"


def format_message(new_by_facility: dict[str, list[matchi.Slot]]) -> str:
    lines = ["🎾 <b>Ny ledig tid på Matchi!</b>"]
    for name, slots in new_by_facility.items():
        lines.append(f"\n<b>{html.escape(name)}</b>")
        lines.extend(format_slot(s) for s in sorted(slots, key=lambda s: (s.start, s.court)))
    return "\n".join(lines)


def run() -> int:
    config = load_config(ROOT / "config.yaml")
    state_path = ROOT / "state.json"
    state = load_state(state_path)
    facilities_state = state.setdefault("facilities", {})
    old_slots = state.get("slots", {})
    new_slots_state: dict[str, dict[str, list[str]]] = {}

    today = datetime.now(matchi.TZ).date()
    days = [today + timedelta(days=i) for i in range(config.days_ahead)]
    new_by_facility: dict[str, list[matchi.Slot]] = {}
    errors: list[str] = []

    with matchi.make_client() as client:
        for fc in config.facilities:
            try:
                if fc.slug not in facilities_state:
                    facility_id, name = matchi.get_facility_info(client, fc.slug)
                    facilities_state[fc.slug] = {"id": facility_id, "name": name}
                info = facilities_state[fc.slug]
            except Exception as e:
                errors.append(f"{fc.slug}: {e}")
                traceback.print_exc()
                continue

            previous = old_slots.get(fc.slug)
            current: dict[str, list[matchi.Slot]] = {}
            new_slots_state[fc.slug] = {}
            for day in days:
                try:
                    slots = matchi.fetch_free_slots(client, info["id"], day, fc.sport)
                except Exception as e:
                    errors.append(f"{fc.slug} {day}: {e}")
                    traceback.print_exc()
                    # Keep what we knew so a later successful fetch is still diffed.
                    if previous and day.isoformat() in previous:
                        new_slots_state[fc.slug][day.isoformat()] = previous[day.isoformat()]
                    continue
                wanted = [s for s in slots if fc.matches(s.start, s.end)]
                current[day.isoformat()] = wanted
                new_slots_state[fc.slug][day.isoformat()] = sorted(s.key for s in wanted)
                print(f"{fc.slug} {day}: {len(slots)} free, {len(wanted)} matching filter")

            new = find_new_slots(previous, current)
            if new:
                new_by_facility.setdefault(info["name"], []).extend(new)

    if new_by_facility:
        message = format_message(new_by_facility)
        print(message)
        notify(message)
    else:
        print("No new free slots.")

    state["slots"] = new_slots_state
    if errors:
        last = state.get("last_error_alert")
        now = datetime.now(timezone.utc)
        if not last or now - datetime.fromisoformat(last) > ERROR_ALERT_INTERVAL:
            notify("⚠️ <b>Matchi-boten fick fel</b>\n" + "\n".join(html.escape(e) for e in errors[:10]))
            state["last_error_alert"] = now.isoformat()
    save_state(state_path, state)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(run())
