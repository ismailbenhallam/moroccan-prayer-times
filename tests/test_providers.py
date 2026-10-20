import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import requests
from conftest import TIMES

from moroccan_prayer_times import providers
from moroccan_prayer_times.providers.base import PrayerTimesProvider


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


@pytest.mark.parametrize(
    "failure",
    [requests.ConnectionError("blocked"), {"data": {}}],
)
def test_aladhan_failures_return_none(failure):
    response = mock.Mock()
    if isinstance(failure, Exception):
        patched = mock.patch("requests.get", side_effect=failure)
    else:
        response.json.return_value = failure
        patched = mock.patch("requests.get", return_value=response)

    with patched:
        assert providers.get_provider("aladhan").fetch_prayer_times(99) is None


def test_provider_from_an_entry_point_is_loaded_on_demand():
    class PluginProvider(PrayerTimesProvider):
        name = "plugin"

        def get_cities(self):
            return {}

        def fetch_prayer_times(self, city_id):
            return TIMES

    entry_point = mock.Mock(load=mock.Mock(return_value=PluginProvider))
    entry_point.name = "plugin"
    with mock.patch.object(providers, "entry_points", return_value=[entry_point]):
        assert "plugin" in providers.available_providers()
        entry_point.load.assert_not_called()

        assert isinstance(providers.get_provider("plugin"), PluginProvider)
    entry_point.load.assert_called_once()
