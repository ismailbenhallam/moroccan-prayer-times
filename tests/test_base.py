import json

import pytest
from conftest import TIMES

from moroccan_prayer_times import settings
from moroccan_prayer_times.providers import base
from moroccan_prayer_times.providers.base import PrayerTimesProvider


class FakeProvider(PrayerTimesProvider):
    name = "fake"

    def __init__(self, times=TIMES):
        self.times = times
        self.fetch_calls = 0

    def get_cities(self):
        return {1: "Rabat"}

    def fetch_prayer_times(self, city_id):
        self.fetch_calls += 1
        return self.times


@pytest.mark.parametrize(
    "now, expected",
    [
        ("18:00", "Al-Ishaa at 19:01 => 1 hour(s) and 1 minute(s) left"),
        ("18:31", "Al-Ishaa at 19:01 => 30 minute(s) left"),
        ("04:03", "Al-Fajr at 05:03 => 1 hour(s) left"),
        ("19:01", "Al-Ishaa now!"),
        # After the last prayer, the next one is tomorrow's Fajr
        ("22:00", "Al-Fajr at 05:03 => 7 hour(s) and 3 minute(s) left"),
    ],
)
def test_next(freeze_time, capsys, now, expected):
    freeze_time(now)

    FakeProvider().next(1)

    assert expected in capsys.readouterr().out


@pytest.mark.parametrize(
    "setting, now, shown",
    [
        ("5", "15:22", "Al-Asr was 5 minute(s) ago"),
        ("5", "15:23", None),
        ("20", "15:37", "Al-Asr was 20 minute(s) ago"),
        ("20", "15:38", None),
        ("5", "15:17", None),  # it is the prayer time itself
        ("5", "19:03", "Al-Ishaa was 2 minute(s) ago"),
        ("5", "12:14", "Al-Dhuhr was 2 minute(s) ago"),
        (None, "15:20", None),  # disabled
        ("0", "15:20", None),  # out of range
        ("21", "15:20", None),
        ("abc", "15:20", None),
    ],
)
def test_next_shows_a_recently_passed_prayer(freeze_time, capsys, setting, now, shown):
    if setting is not None:
        settings.config.set(settings.SECTION_NAME, "past_prayer_minutes", setting)
    freeze_time(now)

    FakeProvider().next(1)

    out = capsys.readouterr().out
    assert ("ago" in out) is (shown is not None)
    if shown:
        assert shown in out
        # the upcoming prayer is still displayed
        assert "left" in out or "now!" in out


@pytest.mark.parametrize(
    "now, marked",
    [("00:30", "Al-Fajr"), ("13:00", "Al-Asr"), ("19:01", "Al-Ishaa")],
)
def test_today_marks_the_next_prayer(freeze_time, capsys, now, marked):
    freeze_time(now)

    FakeProvider().today(1)

    out = capsys.readouterr().out
    assert out.count("<=") == 1
    assert f"{marked} <=" in out


def test_today_marks_nothing_after_the_last_prayer(freeze_time, capsys):
    freeze_time("23:00")

    FakeProvider().today(1)

    assert "<=" not in capsys.readouterr().out


@pytest.mark.parametrize("command", ["today", "next"])
def test_commands_report_missing_data(capsys, command):
    getattr(FakeProvider(times=None), command)(1)

    assert "Failed to retrieve data." in capsys.readouterr().out


def test_prayer_times_are_cached_for_the_day():
    provider = FakeProvider()

    assert provider.get_prayer_times(1) == TIMES
    assert provider.get_prayer_times(1) == TIMES

    assert provider.fetch_calls == 1


def test_cache_is_per_city_and_keeps_only_one_file():
    provider = FakeProvider()

    provider.get_prayer_times(1)
    provider.get_prayer_times(2)

    assert provider.fetch_calls == 2
    assert len(list(base.TIMES_CACHE_FOLDER.iterdir())) == 1


def test_failures_are_not_cached():
    provider = FakeProvider(times=None)

    provider.get_prayer_times(1)
    provider.get_prayer_times(1)

    assert provider.fetch_calls == 2
    assert not base.TIMES_CACHE_FOLDER.exists()


@pytest.mark.parametrize(
    "times",
    [{}, {"a": "05:03"}, {k: "soon" for k in TIMES}],
)
def test_partial_or_garbled_pages_are_not_cached(times):
    provider = FakeProvider(times=times)

    assert provider.get_prayer_times(1) is None
    assert not base.TIMES_CACHE_FOLDER.exists()


def test_corrupt_cache_is_ignored():
    provider = FakeProvider()
    provider.get_prayer_times(1)
    (cache_file,) = base.TIMES_CACHE_FOLDER.iterdir()
    cache_file.write_text("{not json")

    assert provider.get_prayer_times(1) == TIMES
    assert provider.fetch_calls == 2
    assert json.loads(cache_file.read_text()) == TIMES


def test_unwritable_cache_does_not_break_the_command(monkeypatch):
    cache_parent = base.TIMES_CACHE_FOLDER.parent
    cache_parent.mkdir(parents=True, exist_ok=True)
    base.TIMES_CACHE_FOLDER.write_text("a file, not a folder")

    assert FakeProvider().get_prayer_times(1) == TIMES
