"""
Tests for specific internal functions, not overall integration tests.
"""
import pytest 

from pgspecial import iocommands

def test_plain_editor_commands_detected():
    assert not iocommands.editor_command('select * from foo')
    assert not iocommands.editor_command(r'\easy does it')

    assert iocommands.editor_command(r'\e') == r'\e'
    assert iocommands.editor_command(r'\e myfile.txt') == r'\e'
    assert iocommands.editor_command(r'select * from foo \e') == r'\e'

    assert iocommands.editor_command(r'  \e  ') == r'\e'
    assert iocommands.editor_command(r'select * from foo \e  ') == r'\e'


def test_edit_view_command_detected():
    assert iocommands.editor_command(r'\ev myview') == r'\ev'


