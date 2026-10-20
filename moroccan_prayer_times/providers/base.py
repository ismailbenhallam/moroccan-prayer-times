import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import ClassVar

from beautifultable import BeautifulTable, Style
from rich import print

from ..i18n import _
from ..settings import TIMES_CACHE_FOLDER


class PrayerTimesProvider(ABC):
    """Contract of a prayer times source.

    A new provider only has to define `name`, `get_cities` and `fetch_prayer_times`.
    `today` and `next` (the CLI commands) are built on top of them, and can be
    overridden when a provider needs a different behavior.
    """

    # Identifier used in the config file and in the PRAYERTIME_PROVIDER env var
    name: ClassVar[str]

    @abstractmethod
    def get_cities(self) -> dict[int, str] | None:
        """Cities offered by this provider (id -> name), None on failure"""

    @abstractmethod
    def fetch_prayer_times(self, city_id: int) -> dict[str, str] | None:
        """Today's prayer times of the city, None on failure.

        Must contain the 6 times in order (Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha)
        as "HH:MM" strings.
        """

    def get_prayer_times(self, city_id: int) -> dict[str, str] | None:
        """Same as `fetch_prayer_times`, but cached for the day"""
        cache_file = (
            TIMES_CACHE_FOLDER / f"{self.name}_{city_id}_{datetime.today().date()}"
        )
        try:
            with open(cache_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            pass

        prayer_times = self.fetch_prayer_times(city_id)
        if prayer_times:
            self._save_cache(cache_file, prayer_times)
        return prayer_times

    @staticmethod
    def _save_cache(cache_file, prayer_times: dict[str, str]):
        try:
            os.makedirs(TIMES_CACHE_FOLDER, exist_ok=True)
            # Cleaning old cache
            for old_file in TIMES_CACHE_FOLDER.iterdir():
                old_file.unlink(missing_ok=True)
            with open(cache_file, "w", encoding="utf-8") as file:
                json.dump(prayer_times, file)
        except OSError:
            pass

    def today(self, city_id: int) -> None:
        """Display today's prayer times"""
        prayer_times = self.get_prayer_times(city_id)
        if not prayer_times:
            print(_("errors.retrieving_data_failed"))
            return

        now = datetime.now()
        table = BeautifulTable()
        table.set_style(Style.STYLE_BOX_ROUNDED)
        is_next_set = False

        for index, time in enumerate(prayer_times.values()):
            prayer_time = datetime.strptime(time, "%H:%M")
            label = _(f"prayers_by_index._{index}")
            if not is_next_set and (prayer_time.hour, prayer_time.minute) >= (
                now.hour,
                now.minute,
            ):
                is_next_set = True
                label += " <="
            table.rows.append([time, label])
        print(table)

    def next(self, city_id: int) -> None:
        """Display the time remaining until the next prayer"""
        prayer_times = self.get_prayer_times(city_id)
        if not prayer_times:
            print(_("errors.retrieving_data_failed"))
            return

        now = datetime.now()
        times = list(prayer_times.values())
        next_index = next(
            (
                index
                for index, time in enumerate(times)
                if tuple(map(int, time.split(":"))) >= (now.hour, now.minute)
            ),
            None,
        )

        if next_index is not None and times[next_index] == now.strftime("%H:%M"):
            prayer = _(f"prayers_by_index._{next_index}")
            print()
            print(
                f' => [dark_orange bold]{_("success.next_prayer_now", prayer=prayer)}'
                "[/dark_orange bold]"
            )
            print()
            return

        # After the last prayer of the day, the next one is tomorrow's Fajr
        is_tomorrow = next_index is None
        next_index = 0 if is_tomorrow else next_index
        next_time = datetime.strptime(times[next_index], "%H:%M")
        if is_tomorrow:
            next_time += timedelta(days=1)
        remaining = next_time - datetime.strptime(now.strftime("%H:%M"), "%H:%M")
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds // 60) % 60

        if hours == 0:
            path = "success.next_prayer_in_minutes"
        elif minutes == 0:
            path = "success.next_prayer_in_hours"
        else:
            path = "success.next_prayer_in"
        print()
        print(
            " ",
            _(
                path,
                prayer=_(f"prayers_by_index._{next_index}"),
                hours=hours,
                minutes=minutes,
                at=times[next_index],
            ),
        )
        print()
