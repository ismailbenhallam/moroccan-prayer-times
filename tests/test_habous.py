from pathlib import Path
from unittest import mock

import pytest
import requests

from moroccan_prayer_times.providers.habous import HabousProvider

FIXTURE = Path(__file__).parent / "fixtures" / "habous_99.html"
# Real page returned by horaire-api.php?ville=99 (unquoted attributes, Arabic labels)
REAL_HTML = FIXTURE.read_text(encoding="utf-8")


def response(html="", status=200):
    return mock.Mock(content=html.encode(), status_code=status)


def test_prayer_times_are_scraped_in_order():
    with mock.patch("requests.get", return_value=response(REAL_HTML)) as get:
        times = list(HabousProvider().fetch_prayer_times(99).values())

    assert times == ["05:03", "06:26", "12:12", "15:17", "17:48", "19:01"]
    assert get.call_args.args[0].endswith("horaire-api.php?ville=99")


def test_cities_are_scraped_from_unquoted_options():
    with mock.patch("requests.get", return_value=response(REAL_HTML)):
        cities = HabousProvider().get_cities()

    assert cities[1] == "الرباط"
    assert 99 in cities and len(cities) > 100


def test_quoted_and_invalid_options():
    html = (
        '<select name="ville"><option value="index.php?ville=7">A</option>'
        '<option value="index.php?ville=abc">B</option><option>C</option></select>'
    )
    with mock.patch("requests.get", return_value=response(html)):
        assert HabousProvider().get_cities() == {7: "A"}


@pytest.mark.parametrize(
    "failure",
    [response(status=503), requests.ConnectionError("blocked")],
)
def test_failures_return_none(failure):
    kwargs = (
        {"side_effect": failure}
        if isinstance(failure, Exception)
        else {"return_value": failure}
    )
    with mock.patch("requests.get", **kwargs):
        assert HabousProvider().fetch_prayer_times(1) is None
        assert HabousProvider().get_cities() is None


def test_cities_without_the_expected_select_return_none():
    with mock.patch("requests.get", return_value=response("<html></html>")):
        assert HabousProvider().get_cities() is None
