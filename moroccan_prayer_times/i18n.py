import os
from pathlib import Path

import yaml
from pyi18n import PyI18n

from .settings import get_locale

TRANSLATIONS_FOLDER = Path(__file__).resolve().parent / "translations"

# Needed for PyI18n, which resolves load_path relatively to the current directory
os.chdir(Path(os.path.realpath(__file__)).parent)

i18n = PyI18n(available_locales=("ar", "en", "fr"), load_path="translations/")


def _(path: str, **kwargs):
    """Translate a path using the user locale"""
    return i18n.gettext(get_locale(), path, **kwargs)


def english_city_names() -> dict[int, str]:
    """All the known cities (id -> english name), from the bundled translations"""
    with open(TRANSLATIONS_FOLDER / "en.yml", encoding="utf-8") as file:
        cities = yaml.safe_load(file)["en"]["cities"]
    return {int(key.lstrip("_")): name for key, name in cities.items()}
