"""Prayer times providers registry.

Providers are loaded lazily: listing them imports nothing, and only the selected one is
imported when it is requested.

Adding a provider:
  1. Subclass `PrayerTimesProvider` (see `base.py`) and set its `name`.
  2. Make it discoverable, either
     - inside this package: put it in a new module named like the provider (`<name>.py`)
       and decorate it with `@register`, or
     - from an external package, through the `moroccan_prayer_times.providers`
       entry point group (entry point name = provider name, value: "module:ClassName").
"""

import importlib
import pkgutil
from importlib.metadata import entry_points

from .base import PrayerTimesProvider

ENTRY_POINT_GROUP = "moroccan_prayer_times.providers"

_registry: dict[str, type[PrayerTimesProvider]] = {}


class UnknownProviderError(ValueError):
    pass


def register(provider_class: type[PrayerTimesProvider]) -> type[PrayerTimesProvider]:
    """Class decorator making a provider available by its `name`"""
    _registry[provider_class.name.lower()] = provider_class
    return provider_class


def _builtin_names() -> set[str]:
    """Providers shipped in this package, found without importing them"""
    return {m.name for m in pkgutil.iter_modules(__path__) if m.name != "base"}


def _plugins() -> dict:
    """External providers declared as entry points, found without importing them"""
    return {ep.name.lower(): ep for ep in entry_points(group=ENTRY_POINT_GROUP)}


def available_providers() -> list[str]:
    return sorted(_builtin_names() | set(_plugins()) | set(_registry))


def get_provider(name: str) -> PrayerTimesProvider:
    """Instantiate a provider, importing only the module that defines it"""
    name = name.lower()
    if name not in _registry:
        if name in _builtin_names():
            importlib.import_module(f"{__name__}.{name}")  # @register runs here
        elif name in (plugins := _plugins()):
            register(plugins[name].load())
    try:
        return _registry[name]()
    except KeyError:
        raise UnknownProviderError(name) from None
