# -*- coding: utf-8 -*-

import configparser
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import click
import requests
import typer
import urllib3
from beautifultable import BeautifulTable, Style
from bs4 import BeautifulSoup
from pyi18n import PyI18n
from rich import print
from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer
from packaging import version
from . import __version__

# Constants
APP_NAME = "Prayer Times CLI"
APP_FOLDER = "moroccan_prayer_times"
CACHE_FILE_NAME = "moroccan_prayer_times.ini"
CONFIG_FILE = Path(typer.get_app_dir(APP_FOLDER)) / CACHE_FILE_NAME
TIMES_CACHE_FOLDER = Path(typer.get_app_dir(APP_FOLDER)) / "times"
SECTION_NAME = "DEFAULT"
DEFAULT_LOCALE = "en"
GLOBAL_COMMAND = "prayertime"

config = configparser.ConfigParser()
config.read(CONFIG_FILE, encoding="utf-8")


def locale():
    """Get user locale from config file. Fallback is 'en'"""
    return config.get(SECTION_NAME, "locale", fallback=DEFAULT_LOCALE)


# Needed for PyI18n
os.chdir(Path(os.path.realpath(__file__)).parent)

i18n = PyI18n(available_locales=("ar", "en", "fr"), load_path="translations/")


def _(path: str, **kwargs):
    return i18n.gettext(locale(), path, **kwargs)


app = typer.Typer(help=APP_NAME, add_help_option=False, add_completion=False)


def _flush():
    """Save the current config in the config file"""
    os.makedirs(CONFIG_FILE.parent, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        return config.write(file)


class Habous_api:
    @staticmethod
    def get_prayer_times_by_city_id(city_id: int) -> dict[str, str] | None:
        """Get today's Moroccan Prayer Times by city id"""
        today_cache = TIMES_CACHE_FOLDER / f"{city_id}_{datetime.today().date()}"
        try:
            # Reading from cache if it exists
            with open(today_cache, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            pass

        # Endpoint URL
        url = f"https://www.habous.gov.ma/prieres/horaire-api.php?ville={city_id}"

        # Make the HTTP request
        response = requests.get(url, verify=False)

        if response.status_code == 200:
            # Parse HTML content
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract prayer times
            prayer_times = {}
            prayer_table = soup.find("table", class_="horaire")
            if prayer_table:
                rows = prayer_table.find_all("tr")
                for row in rows:
                    columns = row.find_all("td")
                    if len(columns) == 6:
                        prayer_times[columns[0].text.strip().replace(":", "")] = (
                            columns[1].text.strip()
                        )
                        prayer_times[columns[2].text.strip().replace(":", "")] = (
                            columns[3].text.strip()
                        )
                        prayer_times[columns[4].text.strip().replace(":", "")] = (
                            columns[5].text.strip()
                        )
            try:
                # Cleaning old cache
                if os.path.exists(TIMES_CACHE_FOLDER):
                    for old_file_path in os.listdir(TIMES_CACHE_FOLDER):
                        try:
                            os.remove(TIMES_CACHE_FOLDER / old_file_path)
                        except Exception:
                            pass

                # Caching...
                os.makedirs(TIMES_CACHE_FOLDER, exist_ok=True)
                with open(today_cache, "w", encoding="utf-8") as file:
                    json.dump(prayer_times, file)
            except FileNotFoundError:
                pass

            return prayer_times
        else:
            print(_("errors.retrieving_data_failed"))

    @staticmethod
    def get_cities() -> dict[int, str] | None:
        """Get the cities list"""
        url = "https://habous.gov.ma/prieres/index.php"

        response = requests.get(url, verify=False)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            select_ville = soup.find("select", {"name": "ville"})
            if not select_ville:
                return

            options = select_ville.find_all("option")
            ville_options = {}
            for option in options:
                if "value" in option.attrs:
                    value = option["value"]
                    # Extract the last ID assuming it's an integer
                    try:
                        last_id = int(value.split("=")[1])
                        ville_options[last_id] = option.text
                    except ValueError:
                        # Skip if the last part of the value is not an integer
                        pass

            return ville_options


def _prompt_user_for_city(city_options: dict[int, str] | None) -> tuple[int, str]:
    """Prompt the user to choose a city"""
    if city_options is None:
        print(
            f"[bold dark_orange]{_('errors.loading_cities_failed')}[/bold dark_orange]"
        )
        raise typer.Exit(code=1)

    # Translate this list
    for id, city in city_options.items():
        city_options[id] = _(f"cities._{id}")

    # Prompt the user to choose a city
    city_name = inquirer.fuzzy(
        message=_("prompts.choose_city"),
        choices=city_options.values(),
        validate=lambda result: result in city_options.values(),
        qmark="",
        amark="",
    ).execute()

    for city_id in city_options:
        if city_options[city_id] == city_name:
            return city_id, city_name


def _prompt_user_for_locale():
    """Prompt the user to choose a locale from available locales"""
    language = inquirer.rawlist(
        message=_("prompts.choose_locale"),
        choices=i18n.available_locales,
        qmark="",
        amark="",
    ).execute()
    return language


def _city_from_cache_or_prompt_then_save() -> dict[str, str]:
    """Get city from cache and return it. If it's not found, then prompt the user to choose a one"""
    city_id = config.get(SECTION_NAME, "city_id", fallback=None)
    city_name = config.get(SECTION_NAME, "city_name", fallback=None)
    if city_id is None or city_name is None:
        print(f"[bold dark_orange]{_('warnings.city_not_saved')}[/bold dark_orange]")

        answer = inquirer.confirm(
            _("prompts.choose_city_now_and_reuse_it"), default=True, qmark="", amark=""
        ).execute()

        if answer:
            city = _prompt_user_for_city(Habous_api.get_cities())
            city_id, city_name = city
            config.set(SECTION_NAME, "city_id", str(city_id))
            config.set(SECTION_NAME, "city_name", city_name)
            _flush()
            print(_("success.city_saved"))
            return {"city_id": int(city_id), "city_name": city_name}

        # User doesn't want to provide a city
        else:
            raise typer.Exit(code=0)

    # Found in the cache file
    else:
        return {"city_id": int(city_id), "city_name": city_name}


@app.command(
    name="config",
    short_help=_("commands_help.config"),
    help=_("commands_help.config"),
)
def get_config():
    """Show the user config"""
    city_saved = config.get(SECTION_NAME, "city_name", fallback=None)
    print("=> ", _("info.language_saved_is"))
    print("=> ", _("info.city_saved_is", city=city_saved))


@app.command(
    name="setup",
    short_help=_("commands_help.setup"),
    help=_("commands_help.setup"),
)
def setup():
    """Change the user preferences"""
    something_changed = False
    print(_("info.language_saved_is"))

    answer = inquirer.confirm(
        _("prompts.want_to_change_this_param"), default=True, qmark="", amark=""
    ).execute()

    # User wants to save locale
    if answer:
        chosen_locale = _prompt_user_for_locale()

        config.set(SECTION_NAME, "locale", chosen_locale)
        something_changed = True

        # Translate the saved city name
        current_city_id = config.get(SECTION_NAME, "city_id", fallback=None)
        if current_city_id is not None:
            config.set(SECTION_NAME, "city_name", _(f"cities._{current_city_id}"))

    print()
    want_to_change_city = None
    saved_city_name = config.get(SECTION_NAME, "city_name", fallback=None)
    if saved_city_name is not None:
        print(_("info.city_saved_is", city=saved_city_name))
        want_to_change_city = inquirer.confirm(
            _("prompts.want_to_change_this_param"), default=True, qmark="", amark=""
        ).execute()

    if saved_city_name is None or want_to_change_city is True:
        city_id, city_name = _prompt_user_for_city(Habous_api.get_cities())
        config.set(SECTION_NAME, "city_id", str(city_id))
        config.set(SECTION_NAME, "city_name", city_name)
        something_changed = True

    if something_changed:
        _flush()
        print()
        print(_("success.config_saved"))


@app.command(
    name="today",
    short_help=_("commands_help.today"),
    help=_("commands_help.today"),
)
def today_prayer_times():
    """Display today's prayer times"""
    try:
        city_id = _city_from_cache_or_prompt_then_save().get("city_id")
        prayer_times = Habous_api.get_prayer_times_by_city_id(int(city_id))
        if prayer_times:
            current_time = datetime.now()
            current_hour = current_time.hour
            current_minute = current_time.minute

            table = BeautifulTable()
            table.set_style(Style.STYLE_BOX_ROUNDED)
            is_next_set = False

            for index, time in enumerate(prayer_times.values()):
                prayer_date = datetime.strptime(time, "%H:%M")
                prayer_hour = prayer_date.hour
                prayer_minute = prayer_date.minute

                if is_next_set is False and (
                    (prayer_hour == current_hour and prayer_minute == current_minute)
                    or (
                        prayer_hour > current_hour
                        or prayer_hour == current_hour
                        and prayer_minute > current_minute
                    )
                ):
                    is_next_set = True
                    table.rows.append([time, f"{_(f'prayers_by_index._{index}')} <="])
                else:
                    table.rows.append([time, _(f"prayers_by_index._{index}")])
            print(table)
        else:
            print(_("errors.retrieving_data_failed"))
    except Exception:
        pass


@app.command(
    name="next",
    short_help=_("commands_help.next"),
    help=_("commands_help.next"),
)
def next_prayer_time():
    """Display the time remaining until the next prayer"""
    city_id = _city_from_cache_or_prompt_then_save().get("city_id")
    prayer_times = Habous_api.get_prayer_times_by_city_id(int(city_id))
    if prayer_times:
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        next_prayer_time_string = None
        is_now = False
        next_prayer_index = -1

        for index, prayer_time in enumerate(prayer_times.values()):
            prayer_hour, prayer_minute = map(int, prayer_time.split(":"))
            if prayer_hour == current_hour and prayer_minute == current_minute:
                is_now = True
                next_prayer_index = index
                break
            elif prayer_hour > current_hour or (
                prayer_hour == current_hour and prayer_minute > current_minute
            ):
                next_prayer_time_string = f"{prayer_hour:02}:{prayer_minute:02}"
                next_prayer_index = index
                break

        if is_now:
            prayer_name_in_locale = _(f"prayers_by_index._{next_prayer_index}")
            print()
            print(
                f' => [dark_orange bold]{_("success.next_prayer_now", prayer=prayer_name_in_locale)}[/dark_orange bold]'
            )
            print()
        else:
            is_tomorrow = False
            if next_prayer_time_string is None:
                is_tomorrow = True
                for next_fajr_time in prayer_times.values():
                    next_prayer_time_string = next_fajr_time
                    next_prayer_index = 0
                    break

            next_prayer_time = datetime.strptime(next_prayer_time_string, "%H:%M")
            if is_tomorrow:
                next_prayer_time = next_prayer_time + timedelta(days=1)
            time_until_next_prayer = next_prayer_time - datetime.strptime(
                f"{current_hour:02}:{current_minute:02}", "%H:%M"
            )
            prayer = _(f"prayers_by_index._{next_prayer_index}")
            hours = time_until_next_prayer.seconds // 3600
            minutes = (time_until_next_prayer.seconds // 60) % 60
            if hours == 0:
                path = "success.next_prayer_in_minutes"
            elif minutes == 0:
                path = "success.next_prayer_in_hours"
            else:
                path = "success.next_prayer_in"
            print()
            print(
                " => ",
                _(
                    path,
                    prayer=prayer,
                    hours=hours,
                    minutes=minutes,
                ),
            )
            print()
    else:
        print(_("errors.retrieving_data_failed"))


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
    """Show the help message"""
    print(f"[cornflower_blue]{__version__}[/cornflower_blue]")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    _create_config_file_with_default_locale()

    _check_for_upgrade()

    _set_custom_help(ctx)

    """Default command is 'next'"""
    if ctx.invoked_subcommand is not None:
        return
    else:
        print(f'[slate_blue1]{_("commands_help.default_command_note")}[/slate_blue1]')
        next_prayer_time()


def _create_config_file_with_default_locale():
    f"""Create the config file with the default language as {DEFAULT_LOCALE}"""
    if config.get(SECTION_NAME, "locale", fallback=None) is None:
        config.set(SECTION_NAME, "locale", DEFAULT_LOCALE)
        _flush()


def _set_custom_help(ctx):
    ctx.help_option_names = []  # Hide default help option

    class CustomHelp(click.HelpFormatter):
        def write_usage(self, prog: str, args: str = "", prefix=None):
            self.buffer.append(f"Usage: {GLOBAL_COMMAND} COMMAND")

    ctx.formatter_class = CustomHelp


def _check_for_upgrade():
    """Check if a new version is available"""
    latest_upgrade_check_date = config.get(
        SECTION_NAME, "lastest_upgrade_check_time", fallback=None
    )
    today_date = str(datetime.today().date())

    if today_date != latest_upgrade_check_date:
        pypi_url = "https://pypi.org/pypi/moroccan-prayer-times/json"
        try:
            response = requests.get(pypi_url)
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
            _flush()
        except Exception:
            pass


def main():
    urllib3.disable_warnings()
    app()


if __name__ == "__main__":
    main()
