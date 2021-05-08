"""
Tests for specific internal functions, not overall integration tests.
"""
import pytest

from pgspecial import iocommands


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
    subst_query, error = iocommands.subst_favorite_query_args(
        template_query, ("postgres", "42")
    )
    assert error is None
    assert subst_query == "select * from foo where bar = 42 and zoo = 'postgres'"


def test_subst_favorite_query_args_missing_arg():
    template_query = "select * from foo where bar = $2 and zoo = '$1'"
    subst_query, error = iocommands.subst_favorite_query_args(template_query, ("42",))
    assert subst_query is None
    assert error.startswith("missing substitution for ")
