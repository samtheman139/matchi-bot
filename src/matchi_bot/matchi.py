import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.matchi.se"
TZ = ZoneInfo("Europe/Stockholm")
USER_AGENT = "matchi-cancellation-notifier/1.0 (personal use, low frequency)"
REQUEST_DELAY_S = 1.0


class MatchiFormatError(Exception):
    """Raised when Matchi's HTML no longer looks like we expect."""


@dataclass(frozen=True)
class Slot:
    court: str
    start: datetime
    end: datetime
    slot_id: str
    booking_url: str

    @property
    def key(self) -> str:
        return f"{self.court}|{self.start.isoformat()}"


def make_client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
        follow_redirects=True,
    )


def _get(client: httpx.Client, url: str, params: dict | None = None) -> str:
    """GET with one retry and a polite delay before each request."""
    for attempt in range(2):
        time.sleep(REQUEST_DELAY_S)
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError:
            if attempt == 1:
                raise
    raise AssertionError("unreachable")


def get_facility_info(client: httpx.Client, slug: str) -> tuple[str, str]:
    """Return (facility_id, display name) by scraping the facility page."""
    html = _get(client, f"/facilities/{slug}")
    match = re.search(r'facilityId:\s*"(\d+)"', html)
    if not match:
        raise MatchiFormatError(f"Could not find facilityId on page for '{slug}'")
    title = BeautifulSoup(html, "html.parser").find("meta", property="og:title")
    name = title["content"].strip() if title and title.get("content") else slug
    return match.group(1), name


def fetch_free_slots(client: httpx.Client, facility_id: str, day: date, sport: int) -> list[Slot]:
    html = _get(
        client,
        "/book/listSlots",
        params={"wl": "", "facility": facility_id, "date": day.isoformat(), "sport": sport, "week": "", "year": ""},
    )
    return parse_slots(html)


def parse_slots(html: str) -> list[Slot]:
    """Parse the /book/listSlots fragment. It only contains free (bookable) slots."""
    soup = BeautifulSoup(html, "html.parser")
    slots = []
    for row in soup.select("div.panel.collapse li.list-group-item table"):
        link = row.select_one("a[href*='slotIds']")
        cells = row.find_all("td")
        if not link or not cells:
            continue
        href = link["href"]
        # The booking link is /login/auth?returnUrl=/book/index?slotIds=...&start=...&end=...
        return_url = unquote(parse_qs(urlparse(href).query).get("returnUrl", [""])[0])
        query = parse_qs(urlparse(return_url).query)
        try:
            start = datetime.fromtimestamp(int(query["start"][0]) / 1000, TZ)
            end = datetime.fromtimestamp(int(query["end"][0]) / 1000, TZ)
            slot_id = query["slotIds"][0]
        except (KeyError, ValueError) as e:
            raise MatchiFormatError(f"Unexpected booking link format: {href}") from e
        slots.append(
            Slot(
                court=" ".join(cells[0].get_text().split()),
                start=start,
                end=end,
                slot_id=slot_id,
                booking_url=BASE_URL + href,
            )
        )
    if not slots and soup.select("button.btn-slot"):
        raise MatchiFormatError("Found time buttons but could not parse any slots")
    return slots
