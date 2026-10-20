import requests
from bs4 import BeautifulSoup

from . import register
from .base import PrayerTimesProvider


@register
class HabousProvider(PrayerTimesProvider):
    """Official website of the Moroccan Ministry of Habous and Islamic Affairs"""

    name = "habous"
    description = (
        "Official website of the Moroccan Ministry of Habous and Islamic Affairs."
    )

    def get_cities(self) -> dict[int, str] | None:
        try:
            response = requests.get(
                "https://habous.gov.ma/prieres/index.php", verify=False, timeout=(5, 10)
            )
        except requests.RequestException:
            return None
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, "html.parser")
        select_ville = soup.find("select", {"name": "ville"})
        if not select_ville:
            return None

        cities = {}
        for option in select_ville.find_all("option"):
            city_id = self._city_id(option)
            if city_id is not None:
                cities[city_id] = option.text.strip()
        return cities

    @staticmethod
    def _city_id(option) -> int | None:
        # The value looks like "<path>?ville=<id>", but the site sometimes emits
        # "?ville= <id>" unquoted, which the parser splits into a stray attribute
        value = option.attrs.get("value")
        if value is None:
            return None
        id_part = value.split("=", 1)[-1].strip()
        if not id_part:
            id_part = next((name for name in option.attrs if name.isdigit()), "")
        return int(id_part) if id_part.isdigit() else None

    def fetch_prayer_times(self, city_id: int) -> dict[str, str] | None:
        url = f"https://www.habous.gov.ma/prieres/horaire-api.php?ville={city_id}"
        try:
            response = requests.get(url, verify=False, timeout=(5, 10))
        except requests.RequestException:
            return None
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, "html.parser")
        prayer_times = {}
        prayer_table = soup.find("table", class_="horaire")
        if prayer_table:
            for row in prayer_table.find_all("tr"):
                columns = row.find_all("td")
                if len(columns) == 6:
                    for label, value in zip(columns[0::2], columns[1::2]):
                        prayer_times[label.text.strip().replace(":", "")] = (
                            value.text.strip()
                        )
        return prayer_times
