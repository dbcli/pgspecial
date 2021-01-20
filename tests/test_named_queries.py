"""Tests for named queries."""

import pytest
import configparser
import tempfile

from pgspecial.namedqueries import NamedQueries
from pgspecial.main import PGSpecial
from configobj import ConfigObj


@pytest.fixture(scope="module")
def named_query():
    with tempfile.NamedTemporaryFile() as f:
        NamedQueries.instance = NamedQueries.from_config(ConfigObj(f))
        yield
        NamedQueries.instance = None


def test_save_named_queries(named_query):
    PGSpecial().execute(None, "\\ns test select * from foo")
    expected = {"test": "select * from foo"}
    assert NamedQueries.instance.list() == expected


def test_delete_named_queries(named_query):
    PGSpecial().execute(None, "\\ns test_foo select * from foo")
    assert "test_foo" in NamedQueries.instance.list()

    PGSpecial().execute(None, "\\nd test_foo")
    assert "test_foo" not in NamedQueries.instance.list()


def test_print_named_queries(named_query):
    PGSpecial().execute(None, "\\ns test_name select * from bar")
    assert "test_name" in NamedQueries.instance.list()

    result = PGSpecial().execute(None, "\\np test_n.*")
    assert result == [("", [("test_name", "select * from bar")], ["Name", "Query"], "")]

    result = PGSpecial().execute(None, "\\np")
    assert result[0][:3] == (
        None,
        None,
        None,
    )
