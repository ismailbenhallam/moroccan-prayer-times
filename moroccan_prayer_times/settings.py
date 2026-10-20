import configparser
import os
from pathlib import Path

import typer

APP_FOLDER = "moroccan_prayer_times"
CONFIG_FILE = Path(typer.get_app_dir(APP_FOLDER)) / "moroccan_prayer_times.ini"
TIMES_CACHE_FOLDER = Path(typer.get_app_dir(APP_FOLDER)) / "times"
SECTION_NAME = "DEFAULT"
DEFAULT_LOCALE = "en"
DEFAULT_PROVIDER = "habous"
PROVIDER_ENV_VAR = "PRAYERTIME_PROVIDER"
PAST_PRAYER_KEY = "past_prayer_minutes"
PAST_PRAYER_RANGE = range(1, 21)

config = configparser.ConfigParser()
config.read(CONFIG_FILE, encoding="utf-8")


def flush():
    """Save the current config in the config file"""
    os.makedirs(CONFIG_FILE.parent, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        config.write(file)


def get_locale() -> str:
    return config.get(SECTION_NAME, "locale", fallback=DEFAULT_LOCALE)


def get_saved_provider() -> str | None:
    """Provider saved in the config file, if any"""
    return config.get(SECTION_NAME, "provider", fallback=None)


def get_provider_name() -> str:
    """Environment variable first, then the config file, then the default provider"""
    return (
        os.environ.get(PROVIDER_ENV_VAR) or get_saved_provider() or DEFAULT_PROVIDER
    ).lower()


def get_past_prayer_minutes() -> int | None:
    """How long (in minutes) a passed prayer is still displayed by `next`, None if disabled"""
    try:
        minutes = int(config.get(SECTION_NAME, PAST_PRAYER_KEY, fallback=""))
    except ValueError:
        return None
    return minutes if minutes in PAST_PRAYER_RANGE else None
