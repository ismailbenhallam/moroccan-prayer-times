import collections.abc
import configparser
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Any

import requests
import typer
import urllib3
from beautifultable import BeautifulTable, Style
from bs4 import BeautifulSoup
from pyi18n import PyI18n
from rich import print
from rich.prompt import Confirm

# 👇️ Add attributes to `collections` module
# Before importing PyInquirer package
collections.Mapping = collections.abc.Mapping
collections.MutableMapping = collections.abc.MutableMapping
collections.Iterable = collections.abc.Iterable
collections.MutableSet = collections.abc.MutableSet
collections.Callable = collections.abc.Callable
import PyInquirer

# Constants
APP_NAME = "Prayer Times CLI"
APP_FOLDER = "moroccan_prayer_times"
CACHE_FILE_NAME = "moroccan_prayer_times.ini"
CONFIG_FILE = Path(typer.get_app_dir(APP_FOLDER)) / CACHE_FILE_NAME
TIMES_CACHE_FOLDER = Path(typer.get_app_dir(APP_FOLDER)) / "times"
SECTION_NAME = "DEFAULT"
DEFAULT_LOCALE = "en"

config = configparser.ConfigParser()
config.read(CONFIG_FILE, encoding="utf-8")


def locale():
    """Get user locale from config file. Fallback is 'en'"""
    return config.get(SECTION_NAME, "locale", fallback=DEFAULT_LOCALE)


# Needed for PyI18n
os.chdir(Path(os.path.realpath(__file__)).parent)

i18n = PyI18n(available_locales=("ar", "en", "fr"), load_path="translations/")
_: Callable = i18n.gettext

app = typer.Typer(help=APP_NAME, add_help_option=False, add_completion=False)


def _flush():
    """Save the current config in the dedicated file"""
    os.makedirs(CONFIG_FILE.parent, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        return config.write(file)


class Habous_api:
    @staticmethod
    def get_prayer_times_by_city_id(city_id: int) -> dict[str, str] | None:
        """Get today's Moroccan Prayer Times by city id"""
        today_cache = TIMES_CACHE_FOLDER / str(datetime.today().date())
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
            print(_(locale(), "errors.retrieving_data_failed"))

    @staticmethod
    def get_cities() -> dict[int, str] | None:
        """Get the cities list"""
        url = f"https://habous.gov.ma/prieres/index.php"

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
            f"[bold dark_orange]{_(locale(), 'errors.loading_cities_failed')}[/bold dark_orange]"
        )
        raise typer.Exit(code=1)

    # Prompt the user to choose a city
    answers = PyInquirer.prompt(
        [
            {
                "type": "list",
                "name": "city_name",
                "message": _(locale(), "prompts.choose_city"),
                "choices": city_options.values(),
            }
        ]
    )
    city_name = answers["city_name"]

    for city_id in city_options:
        if city_options[city_id] == city_name:
            return city_id, city_name


def _prompt_user_for_locale():
    """Prompt the user to choose a locale from available locales"""
    answers = PyInquirer.prompt(
        [
            {
                "type": "list",
                "name": "language",
                "message": _(locale(), "prompts.choose_locale"),
                "choices": i18n.available_locales,
            }
        ]
    )
    language = answers["language"]
    return language


def _city_from_cache_or_prompt_then_save() -> dict[str, str]:
    """Get city from cache and return it. If it's not found, then prompt the user to choose a one"""
    city_id = config.get(SECTION_NAME, "city_id", fallback=None)
    city_name = config.get(SECTION_NAME, "city_name", fallback=None)
    if city_id is None or city_name is None:
        print(
            f"[bold dark_orange]{_(locale(), 'warnings.city_not_saved')}[/bold dark_orange]"
        )
        answer = Confirm.ask(_(locale(), "prompts.choose_city_now_and_reuse_it"))
        if answer:
            city = _prompt_user_for_city(Habous_api.get_cities())
            if city is not None:
                city_id, city_name = city
                config.set(SECTION_NAME, "city_id", str(city_id))
                config.set(SECTION_NAME, "city_name", city_name)
                _flush()
                print(_(locale(), "success.city_saved"))
                return {"city_id": int(city_id), "city_name": city_name}

            # Canceled
            else:
                raise typer.Exit(code=0)

        # User doesn't want to provide a city
        else:
            raise typer.Exit(code=0)

    # Found in the cache file
    else:
        return {"city_id": int(city_id), "city_name": city_name}


@app.command(
    name="config",
    short_help=_(locale(), "commands_help.config"),
    help=_(locale(), "commands_help.config"),
)
def get_config():
    """Show the user config"""
    city_id = config.get(SECTION_NAME, "city_id", fallback=None)
    city_name = config.get(SECTION_NAME, "city_name", fallback=None)
    locale = config.get(SECTION_NAME, "locale", fallback=None)
    print(
        f"""city_id={city_id}\ncity_name= {city_name}\nlocale= {locale}
    """
    )


@app.command(
    name="setup",
    short_help=_(locale(), "commands_help.setup"),
    help=_(locale(), "commands_help.setup"),
)
def setup():
    """Change the user preferences"""
    try:
        saved_locale = config.get(SECTION_NAME, "locale", fallback=None)
        something_changed = False

        print(_(saved_locale, "info.language_saved_is", language=saved_locale))

        answer = Confirm.ask(_(locale(), "prompts.want_to_change_this_param"))
        # User wants to save locale
        if answer:
            answers = PyInquirer.prompt(
                [
                    {
                        "type": "list",
                        "name": "language",
                        "message": _(saved_locale, "prompts.choose_locale"),
                        "choices": i18n.available_locales,
                    }
                ]
            )
            chosen_locale = answers["language"]
            config.set(SECTION_NAME, "locale", chosen_locale)
            saved_locale = chosen_locale
            something_changed = True

        print()
        want_to_change_city = None
        saved_city_name = config.get(SECTION_NAME, "city_name", fallback=None)
        if saved_city_name is not None:
            print(_(saved_locale, "info.city_saved_is", city=saved_city_name))
            want_to_change_city = Confirm.ask(
                _(saved_locale, "prompts.want_to_change_this_param")
            )

        if saved_city_name is None or want_to_change_city is True:
            city_id, city_name = _prompt_user_for_city(Habous_api.get_cities())
            config.set(SECTION_NAME, "city_id", str(city_id))
            config.set(SECTION_NAME, "city_name", city_name)
            something_changed = True

        if something_changed:
            _flush()
            print()
            print(_(saved_locale, "success.config_saved"))
    except Exception:
        raise


@app.command(
    name="today",
    short_help=_(locale(), "commands_help.today"),
    help=_(locale(), "commands_help.today"),
)
def today_prayer_times():
    """Display today's prayer times"""
    try:
        city_id = _city_from_cache_or_prompt_then_save().get("city_id")
        prayer_times = Habous_api.get_prayer_times_by_city_id(int(city_id))
        if prayer_times:
            table = BeautifulTable()
            table.set_style(Style.STYLE_BOX_ROUNDED)
            for index, time in enumerate(prayer_times.values()):
                table.rows.append([time, _(locale(), f"prayers_by_index._{index}")])
            print(table)
        else:
            print(_(locale(), "errors.retrieving_data_failed"))
    except Exception:
        pass


@app.command(
    name="next",
    short_help=_(locale(), "commands_help.next"),
    help=_(locale(), "commands_help.next"),
)
def next_prayer_time():
    """Display the time remaining until the next prayer"""
    city_id = _city_from_cache_or_prompt_then_save().get("city_id")
    prayer_times = Habous_api.get_prayer_times_by_city_id(int(city_id))
    if prayer_times:
        now = datetime.now()
        current_time = now
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
            prayer_name_in_locale = _(
                locale(), f"prayers_by_index._{next_prayer_index}"
            )
            print(
                f'[dark_orange bold]{_(locale(), "success.next_prayer_now", prayer=prayer_name_in_locale)}[/dark_orange bold]'
            )
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
            hours = time_until_next_prayer.seconds // 3600
            minutes = (time_until_next_prayer.seconds // 60) % 60
            remaining_to_display = f"{hours:02d}:{minutes:02d}"
            print(
                _(
                    locale(),
                    "success.next_prayer_in",
                    prayer=_(locale(), f"prayers_by_index._{next_prayer_index}"),
                    minutes=remaining_to_display,
                )
            )
    else:
        print(_(locale(), "errors.retrieving_data_failed"))


@app.command(
    name="help",
    help="Show this message and exit.",
    short_help=_(locale(), "commands_help.help"),
)
def help(ctx: typer.Context):
    """Show the help message"""
    print(ctx.parent.get_help())


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    f"""Create the config file with the default language as {DEFAULT_LOCALE}"""

    if config.get(SECTION_NAME, "locale", fallback=None) is None:
        config.set(SECTION_NAME, "locale", DEFAULT_LOCALE)
        _flush()

    if ctx.invoked_subcommand is not None:
        return
    else:
        print(f'[bold]{_(locale(), "commands_help.default_command_note")}\n[/bold]')
        next_prayer_time()


def main():
    urllib3.disable_warnings()
    app()


if __name__ == "__main__":
    main()
