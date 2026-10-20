import re
from pathlib import Path

import pytest
import yaml

TRANSLATIONS = (
    Path(__file__).resolve().parents[1] / "moroccan_prayer_times" / "translations"
)
LOCALES = ["en", "fr", "ar"]


def load(locale):
    with open(TRANSLATIONS / f"{locale}.yml", encoding="utf-8") as file:
        return yaml.safe_load(file)[locale]


def flatten(tree, prefix=""):
    for key, value in tree.items():
        if isinstance(value, dict):
            yield from flatten(value, f"{prefix}{key}.")
        else:
            yield f"{prefix}{key}"


@pytest.mark.parametrize("locale", ["fr", "ar"])
def test_locale_has_the_same_messages_as_english(locale):
    # City names are checked by test_every_locale_names_the_same_cities
    def messages(tree):
        return {k for k in flatten(tree) if not k.startswith("cities.")}

    assert messages(load(locale)) == messages(load("en"))


@pytest.mark.parametrize("locale", ["fr", "ar"])
def test_every_locale_names_the_same_cities(locale):
    assert set(load(locale)["cities"]) == set(load("en")["cities"])


@pytest.mark.parametrize("locale", LOCALES)
def test_placeholders_are_the_same_in_every_locale(locale):
    def placeholders(tree):
        return {
            key: set(re.findall(r"{(\w+)}", value))
            for key, value in zip(flatten(tree), _values(tree))
            if isinstance(value, str)
        }

    assert placeholders(load(locale)) == placeholders(load("en"))


def _values(tree):
    for value in tree.values():
        if isinstance(value, dict):
            yield from _values(value)
        else:
            yield value
