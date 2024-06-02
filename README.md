# Moroccan Prayer Times CLI

<!-- [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) -->
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/moroccan-prayer-times?style=for-the-badge)
![PyPI - Version](https://img.shields.io/pypi/v/moroccan-prayer-times?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/ismailbenhallam/prayer-times-cli?style=for-the-badge)

<!-- ![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/ismailbenhallam/prayer-times-cli)
![GitHub Repo stars](https://img.shields.io/github/stars/ismailbenhallam/prayer-times-cli?)-->

A command-line interface (CLI) application to fetch and display Moroccan prayer times for the current day or the next
prayer time remaining, using data provided by the official Moroccan Ministry of Habous and Islamic Affairs
website (https://habous.gov.ma/).

## Features

- Display today's prayer times for a selected Moroccan city
- Show the time remaining until the next prayer
- Configure the preferred city and language
- Caching of fetched prayer times for better performance
- Localization support for Arabic, English, and French languages

## Installation

You can install the package from PyPI using pip:

```shell
pip install moroccan-prayer-times
```

## Usage

After installation, you can run the CLI application with the following commands:

```shell
prayertime help
```

This will display the list of available commands and their descriptions.

### Commands

- `prayertime today`: Display today's prayer times for the configured city.
- `prayertime next`: Show the time remaining until the next prayer.
- `prayertime config`: Display the current configuration (city and language).
- `prayertime setup`: Configure the preferred city and language.
- `prayertime help`: Show the help message.

## Configuration

The first time you run the application, it will prompt you to select a city (**english** is the default language). These
settings will be saved for future use.

You can change the city or the language anytime using the `setup` command.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a
pull request on the [GitHub repository](https://github.com/ismailbenhallam/prayer-times-cli/).

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

This application utilizes the following third-party libraries:

- [Typer](https://typer.tiangolo.com/) for building the CLI
- [Requests](https://requests.readthedocs.io/) for making HTTP requests
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for parsing HTML
- [PyInquirer](https://github.com/CITGuru/PyInquirer) for interactive command-line user prompts
- [Rich](https://github.com/willmcgugan/rich) for styled console output
- [BeautifulTable](https://github.com/pri22296/beautifultable) for rendering tables in the console

