"""
Tests for specific internal functions, not overall integration tests.
"""

import pytest

from pgspecial import iocommands


@pytest.mark.parametrize(
    "command,expected_watch_command,expected_timing",
    [
        ("SELECT * FROM foo \\watch", "SELECT * FROM foo", 2),
        ("SELECT * FROM foo \\watch 123", "SELECT * FROM foo", 123),
        ("SELECT *\nFROM foo \\watch 1", "SELECT *\nFROM foo", 1),
        ("SELECT * FROM foo \\watch   1  ", "SELECT * FROM foo", 1),
        ("SELECT * FROM foo; \\watch    1 ; ", "SELECT * FROM foo;", 1),
        ("SELECT * FROM foo;\\watch 1;", "SELECT * FROM foo;", 1),
    ],
)
def test_get_watch_command(command, expected_watch_command, expected_timing):
    assert iocommands.get_watch_command(command) == (
        expected_watch_command,
        expected_timing,
    )


def test_plain_editor_commands_detected():
    assert not iocommands.editor_command("select * from foo")
    assert not iocommands.editor_command(r"\easy does it")

    assert iocommands.editor_command(r"\e") == r"\e"
    assert iocommands.editor_command(r"\e myfile.txt") == r"\e"
    assert iocommands.editor_command(r"select * from foo \e") == r"\e"

    assert iocommands.editor_command(r"  \e  ") == r"\e"
    assert iocommands.editor_command(r"select * from foo \e  ") == r"\e"


def test_edit_view_command_detected():
    assert iocommands.editor_command(r"\ev myview") == r"\ev"


def test_subst_favorite_query_args():
    template_query = "select * from foo where bar = $2 and zoo = '$1'"
    subst_query, error = iocommands.subst_favorite_query_args(template_query, ("postgres", "42"))
    assert error is None
    assert subst_query == "select * from foo where bar = 42 and zoo = 'postgres'"


def test_subst_favorite_query_args_bad_arg_positional():
    template_query = "select * from foo where bar = $1"
    subst_query, error = iocommands.subst_favorite_query_args(template_query, ("1337", "42"))
    assert subst_query is None
    assert error.startswith("query does not have substitution parameter $2")


@pytest.mark.parametrize(
    "named_query,query_args",
    [
        (
            "select * from foo where bar = $2 and zoo = '$1'",
            ("42",),
        ),
        (
            "select * from foo where bar IN ($@)",
            tuple(),
        ),
        (
            "select * from foo where (id = $1 or id = $2) AND bar IN ($@)",
            ("1337", "42"),
        ),
        (
            "select * from foo where (id = $1 or id = $3) AND bar IN ($@)",
            ("1337", "postgres", "42"),
        ),
    ],
    ids=[
        "missing positional argument",
        "missing aggregation arguments",
        "missing aggregation arguments with positional",
        "missing positional argument after aggregation",
    ],
)
def test_subst_favorite_query_args_missing_arg(named_query, query_args):
    subst_query, error = iocommands.subst_favorite_query_args(named_query, query_args)
    assert subst_query is None
    assert error.startswith("missing substitution for ")


@pytest.mark.parametrize(
    "template_query,query_args,query",
    [
        (
            "select * from foo where bar IN ($*)",
            ("42", "1337"),
            "select * from foo where bar IN (42, 1337)",
        ),
        (
            "select * from foo where bar IN ($@)",
            ("Alice", "Bob", "Charlie"),
            "select * from foo where bar IN ('Alice', 'Bob', 'Charlie')",
        ),
        (
            "select * from foo where bar IN ($@) and (id = $1 or id = $2)",
            ("42", "1337", "Alice", "Bob", "Charlie"),
            "select * from foo where bar IN ('Alice', 'Bob', 'Charlie') and (id = 42 or id = 1337)",
        ),
    ],
    ids=["raw aggregation", "string aggregation", "positional and aggregation"],
)
def test_subst_favorite_query_args_aggregation(template_query, query_args, query):
    subst_query, error = iocommands.subst_favorite_query_args(template_query, query_args)
    assert error is None
    assert subst_query == query
