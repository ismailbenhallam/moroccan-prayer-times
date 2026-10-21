# -*- coding: utf-8 -*-

from datetime import datetime

import requests
import typer
import urllib3
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from packaging import version
from rich import print
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .i18n import _, i18n
from .providers import (
    PrayerTimesProvider,
    UnknownProviderError,
    available_providers,
    get_provider,
)
from .settings import (
    CONFIG_FILE,
    PAST_PRAYER_KEY,
    PAST_PRAYER_RANGE,
    SECTION_NAME,
    config,
    flush,
    get_locale,
    get_past_prayer_minutes,
    get_provider_name,
)

APP_NAME = "Prayer Times CLI"
GLOBAL_COMMAND = "prayertime"

app = typer.Typer(
    help=APP_NAME,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _current_provider() -> PrayerTimesProvider:
    try:
        return get_provider(get_provider_name())
    except UnknownProviderError:
        print(
            "[bold dark_orange]"
            + _(
                "errors.unknown_provider",
                provider=get_provider_name(),
                available=", ".join(available_providers()),
            )
            + "[/bold dark_orange]"
        )
        raise typer.Exit(code=1)


def _city_label(city_id: int, fallback: str) -> str:
    label = _(f"cities._{city_id}")
    return fallback if label.startswith("missing translation") else label


def _prompt_user_for_city(city_options: dict[int, str] | None) -> tuple[int, str]:
    """Prompt the user to choose a city"""
    if city_options is None:
        print(
            f"[bold dark_orange]{_('errors.loading_cities_failed')}[/bold dark_orange]"
        )
        raise typer.Exit(code=1)

    # Translate this list
    # (cities the site added after the translations were bundled keep the site's name)
    translated = {id: _city_label(id, name) for id, name in city_options.items()}

    city_name = inquirer.fuzzy(
        message=_("prompts.choose_city"),
        choices=list(translated.values()),
        validate=lambda result: result in translated.values(),
        qmark="",
        amark="",
    ).execute()

    for city_id, name in translated.items():
        if name == city_name:
            return city_id, city_name


def _prompt_user_for_locale() -> str:
    """Prompt the user to choose a locale from available locales"""
    return inquirer.rawlist(
        message=_("prompts.choose_locale"),
        choices=i18n.available_locales,
        qmark="",
        amark="",
    ).execute()


def _provider_label(name: str) -> str:
    """ "name - description", importing the provider (only needed by `setup`)"""
    try:
        description = get_provider(name).description
    except Exception:  # a broken third-party provider must not break `setup`
        description = ""
    return f"{name} - {description}" if description else name


def _prompt_user_for_provider() -> str:
    """Prompt the user to choose a prayer times provider"""
    names = available_providers()
    return inquirer.rawlist(
        message=_("prompts.choose_provider"),
        choices=[Choice(name, _provider_label(name)) for name in names],
        default=(
            available_providers().index(get_provider_name()) + 1
            if get_provider_name() in available_providers()
            else None
        ),
        qmark="",
        amark="",
    ).execute()


def _past_prayer_info() -> str:
    minutes = get_past_prayer_minutes()
    if minutes is None:
        return _("info.past_prayer_disabled_is")
    return _("info.past_prayer_saved_is", minutes=minutes)


def _prompt_user_for_past_prayer_minutes() -> int | None:
    """Prompt for the number of minutes (None = disabled)"""
    choices = [Choice(None, _("prompts.past_prayer_disabled"))] + [
        Choice(minutes, _("prompts.past_prayer_minutes", minutes=minutes))
        for minutes in PAST_PRAYER_RANGE
    ]
    return inquirer.select(
        message=_("prompts.choose_past_prayer_minutes"),
        choices=choices,
        default=get_past_prayer_minutes(),
        qmark="",
        amark="",
    ).execute()


def _city_from_cache_or_prompt_then_save() -> dict[str, str]:
    """Get city from the config file. If it's not found, then prompt the user to choose a one"""
    city_id = config.get(SECTION_NAME, "city_id", fallback=None)
    city_name = config.get(SECTION_NAME, "city_name", fallback=None)
    unsupported = city_id is not None and not _current_provider().supports_city(
        int(city_id)
    )
    if city_id is None or city_name is None or unsupported:
        warning = "city_not_available" if unsupported else "city_not_saved"
        print(f"[bold dark_orange]{_(f'warnings.{warning}')}[/bold dark_orange]")

        answer = inquirer.confirm(
            _("prompts.choose_city_now_and_reuse_it"), default=True, qmark="", amark=""
        ).execute()

        # User doesn't want to provide a city
        if not answer:
            raise typer.Exit(code=0)

        city_id, city_name = _prompt_user_for_city(_current_provider().get_cities())
        config.set(SECTION_NAME, "city_id", str(city_id))
        config.set(SECTION_NAME, "city_name", city_name)
        flush()
        print(_("success.city_saved"))

    return {"city_id": int(city_id), "city_name": city_name}


@app.command(
    name="config",
    short_help=_("commands_help.config"),
    help=_("commands_details.config", config_file=CONFIG_FILE),
)
def get_config():
    """Show the user config"""
    city_saved = config.get(SECTION_NAME, "city_name", fallback=None)
    print("=> ", _("info.language_saved_is"))
    print("=> ", _("info.city_saved_is", city=city_saved))
    print("=> ", _("info.provider_saved_is", provider=get_provider_name()))
    print("=> ", _past_prayer_info())


@app.command(
    name="setup",
    short_help=_("commands_help.setup"),
    help=_("commands_details.setup", config_file=CONFIG_FILE),
)
def setup():
    """Change the user preferences"""
    something_changed = provider_changed = False
    print(_("info.language_saved_is"))

    answer = inquirer.confirm(
        _("prompts.want_to_change_this_param"), default=True, qmark="", amark=""
    ).execute()

    if answer:
        config.set(SECTION_NAME, "locale", _prompt_user_for_locale())
        something_changed = True

        # Translate the saved city name
        current_city_id = config.get(SECTION_NAME, "city_id", fallback=None)
        if current_city_id is not None:
            config.set(SECTION_NAME, "city_name", _(f"cities._{current_city_id}"))

    print()
    print(_("info.provider_saved_is", provider=get_provider_name()))
    if inquirer.confirm(
        _("prompts.want_to_change_this_param"), default=False, qmark="", amark=""
    ).execute():
        config.set(SECTION_NAME, "provider", _prompt_user_for_provider())
        something_changed = provider_changed = True

    print()
    want_to_change_city = None
    saved_city_name = config.get(SECTION_NAME, "city_name", fallback=None)
    saved_city_id = config.get(SECTION_NAME, "city_id", fallback=None)
    if saved_city_name is not None:
        print(_("info.city_saved_is", city=saved_city_name))
        if (
            provider_changed
            and saved_city_id is not None
            and int(saved_city_id) not in (_current_provider().get_cities() or {})
        ):
            # The new provider doesn't know the saved city
            print(
                f"[bold dark_orange]{_('warnings.city_not_available')}[/bold dark_orange]"
            )
            want_to_change_city = True
        else:
            want_to_change_city = inquirer.confirm(
                _("prompts.want_to_change_this_param"), default=True, qmark="", amark=""
            ).execute()

    if saved_city_name is None or want_to_change_city is True:
        city_id, city_name = _prompt_user_for_city(_current_provider().get_cities())
        config.set(SECTION_NAME, "city_id", str(city_id))
        config.set(SECTION_NAME, "city_name", city_name)
        something_changed = True

    print()
    print(_past_prayer_info())
    if inquirer.confirm(
        _("prompts.want_to_change_this_param"), default=False, qmark="", amark=""
    ).execute():
        minutes = _prompt_user_for_past_prayer_minutes()
        if minutes is None:
            config.remove_option(SECTION_NAME, PAST_PRAYER_KEY)
        else:
            config.set(SECTION_NAME, PAST_PRAYER_KEY, str(minutes))
        something_changed = True

    if something_changed:
        flush()
        print()
        print(_("success.config_saved"))


@app.command(
    name="today",
    short_help=_("commands_help.today"),
    help=_("commands_details.today"),
)
def today_prayer_times():
    """Display today's prayer times"""
    city_id = _city_from_cache_or_prompt_then_save()["city_id"]
    _current_provider().today(city_id)


@app.command(
    name="next",
    short_help=_("commands_help.next"),
    help=_("commands_details.next"),
)
def next_prayer_time(
    short: bool = typer.Option(
        False, "--short", "-s", help=_("commands_help.short"), show_default=False
    ),
):
    """Display the time remaining until the next prayer"""
    city_id = _city_from_cache_or_prompt_then_save()["city_id"]
    _current_provider().next(city_id, compact=short)


@app.command(
    name="help",
    help=_("commands_help.help"),
    short_help=_("commands_help.help"),
)
def display_help(ctx: typer.Context):
    """Show the help message"""
    print(ctx.parent.get_help())


@app.command(
    name="version",
    help=_("commands_help.version"),
    short_help=_("commands_help.version"),
)
def display_version(ctx: typer.Context):
    """Show the version"""
    print(f"[cornflower_blue]{__version__}[/cornflower_blue]")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    _create_config_file_with_default_locale()

    _check_for_upgrade()

    # Default command is 'next'
    if ctx.invoked_subcommand is None:
        print(f'[slate_blue1]{_("commands_help.default_command_note")}[/slate_blue1]')
        next_prayer_time(short=False)


def _create_config_file_with_default_locale():
    """Create the config file with the default language"""
    if config.get(SECTION_NAME, "locale", fallback=None) is None:
        config.set(SECTION_NAME, "locale", get_locale())
        flush()


def _check_for_upgrade():
    """Check if a new version is available"""
    latest_upgrade_check_date = config.get(
        SECTION_NAME, "lastest_upgrade_check_time", fallback=None
    )
    today_date = str(datetime.today().date())

    if today_date != latest_upgrade_check_date:
        pypi_url = "https://pypi.org/pypi/moroccan-prayer-times/json"
        try:
            response = requests.get(pypi_url, timeout=5)
            response.raise_for_status()
            pypi_latest_version = response.json()["info"]["version"]

            if version.parse(pypi_latest_version) > version.parse(__version__):
                Console().print(
                    Panel(
                        f"[cornflower_blue]{_('info.new_version_is_out', version=pypi_latest_version)}",
                        style="green",
                    ),
                    justify="left",
                )

            # Save today as latest check date, check tomorrow again..
            config.set(SECTION_NAME, "lastest_upgrade_check_time", today_date)
            flush()
        except Exception:
            pass


def main():
    urllib3.disable_warnings()
    app()


if __name__ == "__main__":
    main()
