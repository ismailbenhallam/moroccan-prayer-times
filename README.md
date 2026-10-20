# Moroccan Prayer Times CLI

<!-- [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) -->
[![PyPI - Version](https://img.shields.io/pypi/v/moroccan-prayer-times?style=for-the-badge)](https://pypi.org/project/moroccan-prayer-times/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/moroccan-prayer-times?style=for-the-badge)
[![GitHub License](https://img.shields.io/github/license/ismailbenhallam/prayer-times-cli?style=for-the-badge)](https://github.com/ismailbenhallam/prayer-times-cli/?tab=MIT-1-ov-file)

<!-- ![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/ismailbenhallam/prayer-times-cli)
![GitHub Repo stars](https://img.shields.io/github/stars/ismailbenhallam/prayer-times-cli?)-->

A command-line interface (CLI) application to fetch and display Moroccan prayer times for the current day or the next
prayer time remaining. The data comes, by default, from the official [Moroccan Ministry of Habous and Islamic Affairs
website](https://habous.gov.ma/), and other [providers](#providers) can be selected.

## Features

- Display today's prayer times for a selected Moroccan city
- Show the time remaining until the next prayer
- Configure the preferred city, language and prayer times provider
- Pluggable prayer times providers ([Habous](https://habous.gov.ma/) and [Aladhan](https://aladhan.com/prayer-times-api) included)
- Caching the fetched prayer times for better performance
- Localization support for Arabic, English, and French languages

## Installation

You can install the package using either `pipx` or `pip`.

> **Note**: It is highly recommended to install this package using [pipx](https://pipx.pypa.io/stable/). It provides
> an isolated environment for installing and managing command-line tools. It also simplifies running CLIs without
> activating a virtual environment.  
> [Check out this page](https://pipx.pypa.io/stable/comparisons/) to compare **pip** and **pipx**.

### Using pipx

```shell
pipx install moroccan-prayer-times
```

### Using pip

```shell
pip install moroccan-prayer-times
```

## Usage

After the installation, you can run the CLI application with the following command:

```shell
prayertime help
```

This will display the list of available commands and their descriptions.

### Commands

- `prayertime next`: Show the remaining time until the next prayer.
- `prayertime today`: Display today's prayer times for the configured city.
- `prayertime config`: Display the current configuration (city, language and provider).
- `prayertime setup`: Configure the preferred city, language and provider.
- `prayertime help`: Show the help message.

> Note: the default command is `next`.

## Configuration

The first time you run the application, it will prompt you to select a city (**english** is the default language). These
settings will be saved for future use.

You can change the _**city**_, the **_language_** or the **_provider_** anytime using the `setup` command.

### Providers

A provider is the source of the prayer times. The `provider` is part of the config and defaults to `habous`.

| Provider  | Source                                                      |
|-----------|-------------------------------------------------------------|
| `habous`  | [habous.gov.ma](https://habous.gov.ma/) (default)           |
| `aladhan` | [api.aladhan.com](https://aladhan.com/prayer-times-api) (method 21, Morocco), limited to a subset of the cities |

> Aladhan finds a city by its name and cannot resolve many small towns, so `aladhan` only offers the cities that were
> verified to work (`scripts/check_aladhan_cities.sh` and `scripts/reverify_aladhan_cities.sh` re-check them).
> If your saved city isn't available when you switch to it, `setup` asks you to pick another one.

Choose it with `prayertime setup`, or by editing the `provider` entry of the config file. The `PRAYERTIME_PROVIDER`
environment variable overrides the saved value, which is handy for a one-off run:

```shell
PRAYERTIME_PROVIDER=aladhan prayertime today
```

#### Adding a provider

A provider is a subclass of `PrayerTimesProvider` (`moroccan_prayer_times/providers/base.py`). It only has to define:

- `name`: the identifier used in the config,
- `get_cities()`: the available cities (`{id: name}`),
- `fetch_prayer_times(city_id)`: today's six times (Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha) as `"HH:MM"`.

The `today` and `next` commands are implemented by the base class on top of those (with a per-day cache), and can be
overridden if a provider needs something different.

```python
from moroccan_prayer_times.providers import PrayerTimesProvider, register


@register
class MyProvider(PrayerTimesProvider):
    name = "my-provider"

    def get_cities(self):
        return {1: "Rabat"}

    def fetch_prayer_times(self, city_id):
        return {"Fajr": "05:03", "Sunrise": "06:31", "Dhuhr": "12:12",
                "Asr": "15:17", "Maghrib": "17:47", "Isha": "19:01"}
```

Inside this package, put the class in a new module of `moroccan_prayer_times/providers/` named like the provider (e.g. `aladhan.py` for `aladhan`) and decorate it with `@register`: it is found automatically, and only imported when it is selected.

From an external package, declare it as an entry point instead and it will be discovered automatically:

```python
# setup.py of the plugin
entry_points={"moroccan_prayer_times.providers": ["my-provider = my_package.module:MyProvider"]}
```

> City ids are the ones of the Habous website; they are shared by all the providers, which map them to their own
> cities.

> **NOTE:** If you choose to use the Arabic language option with this package, make sure to check the following:
>
> 1. **Terminal Encoding**: Ensure that your terminal is configured to use UTF-8 or another encoding that supports
     Arabic characters. In some terminals or IDEs (like PyCharm), you may need to set the encoding explicitly.
>
> 2. **Font Support**: Verify that your system has fonts installed that support the display of Arabic characters.
     Without proper font support, Arabic text may not render correctly.

## Contributing

To run the tests:

```shell
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests
```

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a
pull request on the [GitHub repository](https://github.com/ismailbenhallam/prayer-times-cli/).

## License

This project is licensed under
the [MIT License](https://github.com/ismailbenhallam/prayer-times-cli/?tab=MIT-1-ov-file).

## Contact

If you have any questions or suggestions, feel free to contact me
at [ismailben44@gmail.com](mailto:ismailben44@gmail.com).