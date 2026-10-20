import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from moroccan_prayer_times import providers
from moroccan_prayer_times.providers.base import PrayerTimesProvider

TIMES = {
    "Fajr": "05:03",
    "Sunrise": "06:31",
    "Dhuhr": "12:12",
    "Asr": "15:17",
    "Maghrib": "17:47",
    "Isha": "19:01",
}


def test_builtin_providers_are_registered():
    assert {"habous", "aladhan"} <= set(providers.available_providers())


def test_unknown_provider():
    with pytest.raises(providers.UnknownProviderError):
        providers.get_provider("nope")


def test_new_provider_gets_today_and_next_for_free(tmp_path, capsys):
    @providers.register
    class FakeProvider(PrayerTimesProvider):
        name = "fake"

        def get_cities(self):
            return {1: "Rabat"}

        def fetch_prayer_times(self, city_id):
            return TIMES

    with mock.patch(
        "moroccan_prayer_times.providers.base.TIMES_CACHE_FOLDER", tmp_path
    ):
        provider = providers.get_provider("fake")
        provider.today(1)
        provider.next(1)

    assert "19:01" in capsys.readouterr().out
    assert list(tmp_path.glob("fake_1_*"))


def test_aladhan_parsing():
    response = mock.Mock()
    response.json.return_value = {
        "data": {"timings": {**TIMES, "Isha": "19:01 (+01)", "Imsak": "04:53"}}
    }
    with mock.patch("requests.get", return_value=response) as get:
        result = providers.get_provider("aladhan").fetch_prayer_times(99)

    assert result == TIMES
    assert get.call_args.kwargs["params"] == {
        "city": "Meknes",
        "country": "MA",
        "method": 21,
    }


def test_aladhan_only_offers_verified_cities():
    provider = providers.get_provider("aladhan")
    cities = provider.get_cities()

    assert cities[99] == "Meknes"
    assert 5 not in cities  # Oualidia: not resolved by Aladhan
    with mock.patch("requests.get") as get:
        assert provider.fetch_prayer_times(5) is None
    get.assert_not_called()


def test_only_the_requested_provider_is_imported():
    code = (
        "import sys\n"
        "from moroccan_prayer_times.providers import get_provider\n"
        "get_provider('habous')\n"
        "assert 'moroccan_prayer_times.providers.habous' in sys.modules\n"
        "assert 'moroccan_prayer_times.providers.aladhan' not in sys.modules\n"
    )
    # The package changes the working directory on import, so the root is given explicitly
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "-c", code], check=True, cwd=root)


@pytest.mark.parametrize("name", providers._builtin_names())
def test_builtin_module_name_matches_provider_name(name):
    provider = providers.get_provider(name)

    assert provider.name == name
    assert isinstance(provider, PrayerTimesProvider)
