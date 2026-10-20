"""Prayer times providers registry.

Adding a provider:
  1. Subclass `PrayerTimesProvider` (see `base.py`) and set its `name`.
  2. Register it, either
     - inside this package: decorate it with `@register` in a new module here, it is
       discovered automatically, or
     - from an external package, through the `moroccan_prayer_times.providers`
       entry point group (value: "module:ClassName").
"""

import importlib
import pkgutil
from importlib.metadata import entry_points

from .base import PrayerTimesProvider

ENTRY_POINT_GROUP = "moroccan_prayer_times.providers"

_registry: dict[str, type[PrayerTimesProvider]] = {}
_plugins_loaded = False


class UnknownProviderError(ValueError):
    pass


def register(provider_class: type[PrayerTimesProvider]) -> type[PrayerTimesProvider]:
    """Class decorator making a provider available by its `name`"""
    _registry[provider_class.name.lower()] = provider_class
    return provider_class


def _load_providers():
    global _plugins_loaded
    if _plugins_loaded:
        return
    _plugins_loaded = True

    # Importing each module of this package registers its providers (see @register)
    for module in pkgutil.iter_modules(__path__):
        if module.name == "base":
            continue
        try:
            importlib.import_module(f"{__name__}.{module.name}")
        except Exception:
            # A broken provider must not break the CLI
            pass

    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        try:
            register(entry_point.load())
        except Exception:
            # A broken third-party plugin must not break the CLI
            pass


def available_providers() -> list[str]:
    _load_providers()
    return sorted(_registry)


def get_provider(name: str) -> PrayerTimesProvider:
    _load_providers()
    try:
        return _registry[name.lower()]()
    except KeyError:
        raise UnknownProviderError(name) from None
