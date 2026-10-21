from unittest import mock

import pytest
import requests
from conftest import TIMES
from typer.testing import CliRunner

from moroccan_prayer_times import main, providers, settings
from moroccan_prayer_times.providers.base import PrayerTimesProvider

runner = CliRunner()


@providers.register
class CliFakeProvider(PrayerTimesProvider):
    name = "clifake"

    def get_cities(self):
        return {1: "Rabat", 99: "Meknes"}

    def fetch_prayer_times(self, city_id):
        return TIMES


class FakeInquirer:
    """Answers the prompts in order, whatever their type"""

    def __init__(self, *answers):
        self.answers = list(answers)

    def _prompt(self, *args, **kwargs):
        return mock.Mock(execute=lambda: self.answers.pop(0))

    confirm = rawlist = fuzzy = select = _prompt


def save(**values):
    for key, value in values.items():
        settings.config.set(settings.SECTION_NAME, key, value)


@pytest.fixture
def clifake(monkeypatch):
    monkeypatch.setenv(settings.PROVIDER_ENV_VAR, "clifake")
    save(city_id="1", city_name="Rabat")


def test_version():
    result = runner.invoke(main.app, ["version"])

    assert result.exit_code == 0
    assert main.__version__ in result.output


@pytest.mark.parametrize("args", [["today"], ["next"], []])
def test_commands_use_the_selected_provider(clifake, freeze_time, args):
    freeze_time("18:00")

    result = runner.invoke(main.app, args)

    assert result.exit_code == 0
    assert "19:01" in result.output


def test_config_shows_the_provider(clifake):
    result = runner.invoke(main.app, ["config"])

    assert "clifake" in result.output
    assert "Rabat" in result.output


def test_provider_choices_show_the_descriptions(monkeypatch):
    captured = {}

    def rawlist(**kwargs):
        captured.update(kwargs)
        return mock.Mock(execute=lambda: "habous")

    monkeypatch.setattr(main.inquirer, "rawlist", rawlist)

    assert main._prompt_user_for_provider() == "habous"
    labels = {choice.value: choice.name for choice in captured["choices"]}
    assert labels["aladhan"].startswith("aladhan - ")
    assert labels["habous"].startswith("habous - ") and len(labels["habous"]) > 20


def test_provider_without_description_or_broken_shows_its_name(monkeypatch):
    monkeypatch.setattr(main, "get_provider", mock.Mock(side_effect=ImportError))

    assert main._provider_label("broken") == "broken"


def test_unknown_provider_is_reported(monkeypatch):
    monkeypatch.setenv(settings.PROVIDER_ENV_VAR, "nope")
    save(city_id="1", city_name="Rabat")

    result = runner.invoke(main.app, ["today"])

    assert result.exit_code == 1
    assert "Unknown provider 'nope'" in result.output
    assert "aladhan" in result.output


def test_missing_city_can_be_declined(monkeypatch):
    monkeypatch.setattr(main, "inquirer", FakeInquirer(False))

    result = runner.invoke(main.app, ["next"])

    assert result.exit_code == 0
    assert "City information not found!" in result.output


def test_missing_city_is_prompted_then_saved(monkeypatch):
    monkeypatch.setenv(settings.PROVIDER_ENV_VAR, "clifake")
    monkeypatch.setattr(main, "inquirer", FakeInquirer(True, "Meknes"))

    result = runner.invoke(main.app, ["today"])

    assert result.exit_code == 0
    assert settings.config.get(settings.SECTION_NAME, "city_id") == "99"
    assert "19:01" in result.output


def test_saved_city_unsupported_by_the_provider_is_asked_again(monkeypatch):
    monkeypatch.setenv(settings.PROVIDER_ENV_VAR, "aladhan")
    settings.config.set(settings.SECTION_NAME, "city_id", "999")
    settings.config.set(settings.SECTION_NAME, "city_name", "Gone")
    monkeypatch.setattr(main, "inquirer", FakeInquirer(True, "Meknes"))
    monkeypatch.setattr("requests.get", mock.Mock(side_effect=requests.ConnectionError))

    result = runner.invoke(main.app, ["today"])

    assert "not available with this provider" in result.output
    assert settings.config.get(settings.SECTION_NAME, "city_id") == "99"


def test_city_added_by_the_site_keeps_its_own_name():
    assert main._city_label(99, "x") == "Meknes"
    assert main._city_label(99999, "Nouvelle") == "Nouvelle"


def test_setup_saves_the_provider_and_asks_again_for_an_unsupported_city(monkeypatch):
    # Oualidia (5) is not supported by Aladhan
    save(locale="en", city_id="5", city_name="Oualidia")
    # keep the language? no | change the provider? yes | provider | pick a city | city
    monkeypatch.setattr(
        main, "inquirer", FakeInquirer(False, True, "aladhan", "Meknes", False)
    )

    result = runner.invoke(main.app, ["setup"])

    assert result.exit_code == 0
    assert "not available with this provider" in result.output
    assert settings.config.get(settings.SECTION_NAME, "provider") == "aladhan"
    assert settings.config.get(settings.SECTION_NAME, "city_id") == "99"
    assert "provider = aladhan" in settings.CONFIG_FILE.read_text()


def test_setup_keeps_a_supported_city_without_asking(monkeypatch):
    save(locale="en", city_id="99", city_name="Meknes")
    # language: no | provider: yes -> aladhan | change the city: no
    monkeypatch.setattr(
        main, "inquirer", FakeInquirer(False, True, "aladhan", False, False)
    )

    result = runner.invoke(main.app, ["setup"])

    assert result.exit_code == 0
    assert settings.config.get(settings.SECTION_NAME, "city_id") == "99"
    assert settings.config.get(settings.SECTION_NAME, "provider") == "aladhan"


def test_setup_changes_the_language_and_translates_the_saved_city(monkeypatch):
    save(locale="en", city_id="99", city_name="Meknes")
    # change the language: yes -> fr | change the provider: no | change the city: no
    monkeypatch.setattr(main, "inquirer", FakeInquirer(True, "fr", False, False, False))

    result = runner.invoke(main.app, ["setup"])

    assert result.exit_code == 0
    assert settings.config.get(settings.SECTION_NAME, "locale") == "fr"
    assert settings.config.get(settings.SECTION_NAME, "city_name") == "Meknès"


def test_setup_enables_then_disables_the_past_prayer_display(monkeypatch):
    save(locale="en", city_id="99", city_name="Meknes")
    # language: no | provider: no | city: no | past prayer: yes -> 7 minutes
    monkeypatch.setattr(main, "inquirer", FakeInquirer(False, False, False, True, 7))
    runner.invoke(main.app, ["setup"])
    assert settings.get_past_prayer_minutes() == 7
    assert "past_prayer_minutes = 7" in settings.CONFIG_FILE.read_text()

    # ... then past prayer: yes -> disabled (None)
    monkeypatch.setattr(main, "inquirer", FakeInquirer(False, False, False, True, None))
    runner.invoke(main.app, ["setup"])
    assert settings.get_past_prayer_minutes() is None
    assert "past_prayer_minutes" not in settings.CONFIG_FILE.read_text()


def test_config_shows_the_past_prayer_setting():
    save(city_id="99", city_name="Meknes", past_prayer_minutes="5")

    assert "5 minute(s)" in runner.invoke(main.app, ["config"]).output


def pypi_response(latest):
    return mock.Mock(json=lambda: {"info": {"version": latest}})


def test_upgrade_check_announces_a_newer_version(monkeypatch):
    settings.config.remove_option(settings.SECTION_NAME, "lastest_upgrade_check_time")

    with mock.patch("requests.get", return_value=pypi_response("99.0.0")) as get:
        result = runner.invoke(main.app, ["version"])

    get.assert_called_once()
    assert "99.0.0" in result.output
    assert settings.config.get(settings.SECTION_NAME, "lastest_upgrade_check_time")


def test_upgrade_check_is_silent_when_offline():
    settings.config.remove_option(settings.SECTION_NAME, "lastest_upgrade_check_time")

    with mock.patch("requests.get", side_effect=OSError("offline")):
        result = runner.invoke(main.app, ["version"])

    assert result.exit_code == 0
    assert main.__version__ in result.output


def test_upgrade_check_runs_once_a_day():
    with mock.patch("requests.get") as get:
        runner.invoke(main.app, ["version"])

    get.assert_not_called()
