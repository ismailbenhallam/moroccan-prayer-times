from datetime import datetime

import pytest

from moroccan_prayer_times import settings
from moroccan_prayer_times.providers import base

TIMES = {
    "Fajr": "05:03",
    "Sunrise": "06:31",
    "Dhuhr": "12:12",
    "Asr": "15:17",
    "Maghrib": "17:47",
    "Isha": "19:01",
}


@pytest.fixture(autouse=True)
def isolated_user_data(tmp_path, monkeypatch):
    """Never read or write the real config / cache of the user running the tests"""
    monkeypatch.setattr(settings, "CONFIG_FILE", tmp_path / "config" / "test.ini")
    monkeypatch.setattr(base, "TIMES_CACHE_FOLDER", tmp_path / "times")
    monkeypatch.delenv(settings.PROVIDER_ENV_VAR, raising=False)

    # The config object is shared by several modules, so it is emptied in place
    saved = dict(settings.config[settings.SECTION_NAME])
    settings.config[settings.SECTION_NAME].clear()
    # Skips the daily upgrade check, which would call PyPI
    settings.config.set(
        settings.SECTION_NAME,
        "lastest_upgrade_check_time",
        str(datetime.today().date()),
    )
    yield
    settings.config[settings.SECTION_NAME].clear()
    settings.config[settings.SECTION_NAME].update(saved)


@pytest.fixture
def freeze_time(monkeypatch):
    """freeze_time("18:31") makes the providers believe it is 18:31"""

    def freeze(hhmm: str):
        hour, minute = map(int, hhmm.split(":"))

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 20, hour, minute)

        monkeypatch.setattr(base, "datetime", FrozenDatetime)

    return freeze
