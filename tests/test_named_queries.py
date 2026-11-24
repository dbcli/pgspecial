"""Tests for named queries."""

import pytest
import tempfile

from pgspecial.namedqueries import NamedQueries
from pgspecial.main import PGSpecial
from pgspecial.iocommands import subst_favorite_query_args
from configobj import ConfigObj
from dbutils import dbtest


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


def test_favorite_query_with_optional_parameter_supplied():
    query = "select * from abc where ($?1 is null or name like '%$?1%')"
    result = subst_favorite_query_args(query, ["foo"])
    assert result == [
        "select * from abc where (foo is null or name like '%foo%')",
        None,
    ]


def test_favorite_query_with_optional_parameter_missing_becomes_null():
    query = "select * from abc where ($?1 is null or name like '%$?1%')"
    result = subst_favorite_query_args(query, [])
    assert result == [
        "select * from abc where (null is null or name like '%null%')",
        None,
    ]


def test_favorite_query_optional_and_mandatory_parameters():
    query = "select * from t where a > $1 and ($?2 is null or b like '%$?2%')"
    assert subst_favorite_query_args(query, ["5"])[0] == ("select * from t where a > 5 and (null is null or b like '%null%')")
    assert subst_favorite_query_args(query, ["5", "x"])[0] == ("select * from t where a > 5 and (x is null or b like '%x%')")


def test_favorite_query_extra_argument_beyond_placeholders_errors():
    query = "select * from t where a > $1 and b like '%$?2%'"
    result = subst_favorite_query_args(query, ["5", "x", "y"])
    assert result[0] is None
    assert "$3" in result[1] and "$?3" in result[1]


@dbtest
def test_run_named_query_with_only_optional_param(named_query, connection):
    # A saved query with only optional parameters must still reach the
    # substitution step; the old gate only fired on a literal $1.
    cur = connection.cursor()

    cur.execute("DROP TABLE IF EXISTS nq_optional_test")
    cur.execute("CREATE TABLE nq_optional_test (i int)")
    cur.execute("INSERT INTO nq_optional_test VALUES (1), (10)")

    save = r"\ns nq_opt select * from nq_optional_test where ($?1 is null or i > $?1)"
    PGSpecial().execute(cur, save)

    list(PGSpecial().execute(cur, r"\n nq_opt"))
    rows = cur.fetchall()
    assert sorted(r[0] for r in rows) == [1, 10]

    list(PGSpecial().execute(cur, r"\n nq_opt 5"))
    rows = cur.fetchall()
    assert [r[0] for r in rows] == [10]

    cur.execute("DROP TABLE IF EXISTS nq_optional_test")
