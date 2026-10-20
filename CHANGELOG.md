# Changelog

## 2.1.0

### Added
- `prayertime next` can also display a prayer that passed less than X minutes ago
  (`Al-Asr was 3 minute(s) ago`). X is between 1 and 20, and the feature is disabled
  by default. Configure it with `prayertime setup` (`past_prayer_minutes` in the config file).

## 2.0.0

### Added
- **Configurable prayer times provider.** Choose it with `prayertime setup`, the
  `provider` entry of the config file, or the `PRAYERTIME_PROVIDER` environment
  variable (which takes precedence).
- **`aladhan` provider** ([api.aladhan.com](https://aladhan.com/prayer-times-api)),
  as an alternative to `habous`. It supports 82 Moroccan cities; the others are
  not offered because the API cannot resolve them reliably.
- **Pluggable providers.** A provider implements `get_cities` and
  `fetch_prayer_times`, and gets `today` and `next` for free. Providers are loaded
  lazily by name and can be shipped as separate packages through the
  `moroccan_prayer_times.providers` entry point group. See the README.
- Test suite, run in CI before publishing.

### Changed
- `habous` stays the default provider, so nothing changes for existing users.
- When the provider changes and the saved city is not available with it, you are
  asked to pick a new city.
- Prayer times are cached per provider and city for the day.
- Python 3.11 or newer is required. PyYAML is a new dependency.

### Fixed
- The Habous city list was empty when the site emitted unquoted
  `value=...?ville= <id>` options.
- A page with missing or malformed times is no longer cached.
- An unusable cache folder no longer crashes the commands.
- When data cannot be retrieved, a hint now suggests checking the city or running
  `prayertime setup`.
- Cities the site adds without a bundled translation show the site's name.
- French error messages were not displayed (`error:` key renamed to `errors:`),
  and one of them was wrong.
