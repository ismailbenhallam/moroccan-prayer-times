# Moroccan Prayer Times CLI

<!-- [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) -->
[![PyPI - Version](https://img.shields.io/pypi/v/moroccan-prayer-times?style=for-the-badge)](https://pypi.org/project/moroccan-prayer-times/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/moroccan-prayer-times?style=for-the-badge)
[![GitHub License](https://img.shields.io/github/license/ismailbenhallam/prayer-times-cli?style=for-the-badge)](https://github.com/ismailbenhallam/prayer-times-cli/?tab=MIT-1-ov-file)

<!-- ![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/ismailbenhallam/prayer-times-cli)
![GitHub Repo stars](https://img.shields.io/github/stars/ismailbenhallam/prayer-times-cli?)-->

A command-line interface (CLI) application to fetch and display Moroccan prayer times for the current day or the next
prayer time remaining, using data provided by the official [Moroccan Ministry of Habous and Islamic Affairs
website](https://habous.gov.ma/).

## Features

- Display today's prayer times for a selected Moroccan city
- Show the time remaining until the next prayer
- Configure the preferred city and language
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
- `prayertime config`: Display the current configuration (city and language).
- `prayertime setup`: Configure the preferred city and language.
- `prayertime help`: Show the help message.

> Note: the default command is `next`.

## Configuration

The first time you run the application, it will prompt you to select a city (**english** is the default language). These
settings will be saved for future use.

You can change the _**city**_ or the **_language_** anytime using the `setup` command.

> **NOTE:** If you choose to use the Arabic language option with this package, make sure to check the following:
>
> 1. **Terminal Encoding**: Ensure that your terminal is configured to use UTF-8 or another encoding that supports
     Arabic characters. In some terminals or IDEs (like PyCharm), you may need to set the encoding explicitly.
>
> 2. **Font Support**: Verify that your system has fonts installed that support the display of Arabic characters.
     Without proper font support, Arabic text may not render correctly.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a
pull request on the [GitHub repository](https://github.com/ismailbenhallam/prayer-times-cli/).

## License

This project is licensed under
the [MIT License](https://github.com/ismailbenhallam/prayer-times-cli/?tab=MIT-1-ov-file).

## Contact

If you have any questions or suggestions, feel free to contact me
at [ismailben44@gmail.com](mailto:ismailben44@gmail.com).