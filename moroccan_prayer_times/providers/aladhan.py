from datetime import datetime

import requests

from ..i18n import english_city_names
from . import register
from .base import PrayerTimesProvider

# Method 21 = Morocco, Ministry of Habous and Islamic Affairs
CALCULATION_METHOD = 21
PRAYERS = ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")

# Aladhan finds the city by name (geocoding) and fails for many small towns (HTTP 503), so only
# the cities that were verified to work are offered. Checked with scripts/check_aladhan_cities.sh
# fmt: off
SUPPORTED_CITY_IDS = frozenset({
    1, 2, 3, 4, 6, 7, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 25, 26, 27,
    28, 29, 31, 32, 35, 38, 39, 40, 41, 42, 44, 47, 49, 50, 51, 52, 53, 54, 58, 59,
    61, 65, 66, 68, 70, 73, 74, 77, 78, 79, 81, 82, 89, 99, 100, 103, 104, 106, 107,
    108, 109, 111, 112, 113, 116, 117, 119, 128, 132, 136, 137, 138, 148, 149, 152,
    156, 157, 158, 159, 165,
})
# fmt: on


@register
class AladhanProvider(PrayerTimesProvider):
    """https://aladhan.com/prayer-times-api"""

    name = "aladhan"

    def get_cities(self) -> dict[int, str] | None:
        # Aladhan has no cities endpoint, so the bundled list is used
        return {
            city_id: name
            for city_id, name in english_city_names().items()
            if city_id in SUPPORTED_CITY_IDS
        }

    def fetch_prayer_times(self, city_id: int) -> dict[str, str] | None:
        city = english_city_names().get(city_id)
        if city is None or city_id not in SUPPORTED_CITY_IDS:
            return None

        today = datetime.today().strftime("%d-%m-%Y")
        try:
            response = requests.get(
                f"https://api.aladhan.com/v1/timingsByCity/{today}",
                params={"city": city, "country": "MA", "method": CALCULATION_METHOD},
                timeout=15,
            )
            response.raise_for_status()
            timings = response.json()["data"]["timings"]
            # Values can have a timezone suffix, e.g. "19:01 (+01)"
            return {prayer: timings[prayer].split(" ")[0] for prayer in PRAYERS}
        except (requests.RequestException, KeyError, ValueError):
            return None
