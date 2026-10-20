import pytest

from moroccan_prayer_times import settings


def test_provider_defaults_to_habous():
    assert settings.get_provider_name() == "habous"


def test_provider_from_config():
    settings.config.set(settings.SECTION_NAME, "provider", "aladhan")

    assert settings.get_provider_name() == "aladhan"


def test_env_var_overrides_config(monkeypatch):
    settings.config.set(settings.SECTION_NAME, "provider", "habous")
    monkeypatch.setenv(settings.PROVIDER_ENV_VAR, "Aladhan")

    assert settings.get_provider_name() == "aladhan"


def test_flush_writes_the_config_file():
    settings.config.set(settings.SECTION_NAME, "provider", "aladhan")

    settings.flush()

    assert "provider = aladhan" in settings.CONFIG_FILE.read_text()


@pytest.mark.parametrize("locale", ["en", "fr", "ar"])
def test_locale(locale):
    settings.config.set(settings.SECTION_NAME, "locale", locale)

    assert settings.get_locale() == locale
