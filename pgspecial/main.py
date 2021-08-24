from __future__ import unicode_literals
import os
import logging
from collections import namedtuple

from . import export
from .help.commands import helpcommands

log = logging.getLogger(__name__)

NO_QUERY = 0
PARSED_QUERY = 1
RAW_QUERY = 2

PAGER_ALWAYS = 2
PAGER_LONG_OUTPUT = 1
PAGER_OFF = 0

PAGER_MSG = {
    PAGER_OFF: "Pager usage is off.",
    PAGER_LONG_OUTPUT: "Pager is used for long output.",
    PAGER_ALWAYS: "Pager is always used.",
}

SpecialCommand = namedtuple(
    "SpecialCommand",
    ["handler", "syntax", "description", "arg_type", "hidden", "case_sensitive"],
)


@export
class CommandNotFound(Exception):
    pass


@export
class PGSpecial(object):

    # Default static commands that don't rely on PGSpecial state are registered
    # via the special_command decorator and stored in default_commands
    default_commands = {}

    def __init__(self):
        self.timing_enabled = True

        self.commands = self.default_commands.copy()
        self.timing_enabled = False
        self.expanded_output = False
        self.auto_expand = False
        self.pager_config = PAGER_ALWAYS
        self.pager = os.environ.get("PAGER", "")

        self.register(
            self.show_help, "\\?", "\\?", "Show Commands.", arg_type=PARSED_QUERY
        )

        self.register(
            self.toggle_expanded_output,
            "\\x",
            "\\x",
            "Toggle expanded output.",
            arg_type=PARSED_QUERY,
        )

        self.register(
            self.call_pset,
            "\\pset",
            "\\pset [key] [value]",
            "A limited version of traditional \\pset",
            arg_type=PARSED_QUERY,
        )

        self.register(
            self.show_command_help,
            "\\h",
            "\\h",
            "Show SQL syntax and help.",
            arg_type=PARSED_QUERY,
        )

        self.register(
            self.toggle_timing,
            "\\timing",
            "\\timing",
            "Toggle timing of commands.",
            arg_type=NO_QUERY,
        )

        self.register(
            self.set_pager,
            "\\pager",
            "\\pager [command]",
            "Set PAGER. Print the query results via PAGER.",
            arg_type=PARSED_QUERY,
        )

    def register(self, *args, **kwargs):
        register_special_command(*args, command_dict=self.commands, **kwargs)

    def execute(self, cur, sql):
        commands = self.commands
        command, verbose, pattern = parse_special_command(sql)

        if (command not in commands) and (command.lower() not in commands):
            raise CommandNotFound

        try:
            special_cmd = commands[command]
        except KeyError:
            special_cmd = commands[command.lower()]
            if special_cmd.case_sensitive:
                raise CommandNotFound("Command not found: %s" % command)

        if special_cmd.arg_type == NO_QUERY:
            return special_cmd.handler()
        elif special_cmd.arg_type == PARSED_QUERY:
            return special_cmd.handler(cur=cur, pattern=pattern, verbose=verbose)
        elif special_cmd.arg_type == RAW_QUERY:
            return special_cmd.handler(cur=cur, query=sql)

    def show_help(self, pattern, **_):
        if pattern.strip():
            return self.show_command_help(pattern)

        headers = ["Command", "Description"]
        result = []

        for _, value in sorted(self.commands.items()):
            if not value.hidden:
                result.append((value.syntax, value.description))
        return [(None, result, headers, None)]

    def show_command_help_listing(self):
        table = chunks(sorted(helpcommands.keys()), 6)
        return [(None, table, [], None)]

    def show_command_help(self, pattern, **_):
        command = pattern.strip().upper()
        message = ""

        if not command:
            return self.show_command_help_listing()

        if command in helpcommands:
            helpcommand = helpcommands[command]

            if "description" in helpcommand:
                message += helpcommand["description"]
            if "synopsis" in helpcommand:
                message += "\nSyntax:\n"
                message += helpcommand["synopsis"]
        else:
            message = 'No help available for "%s"' % pattern
            message += "\nTry \\h with no arguments to see available help."

        return [(None, None, None, message)]

    def toggle_expanded_output(self, pattern, **_):
        flag = pattern.strip()
        if flag == "auto":
            self.auto_expand = True
            self.expanded_output = False
            return [(None, None, None, "Expanded display is used automatically.")]
        elif flag == "off":
            self.expanded_output = False
        elif flag == "on":
            self.expanded_output = True
        else:
            self.expanded_output = not (self.expanded_output or self.auto_expand)

        self.auto_expand = self.expanded_output
        message = "Expanded display is "
        message += "on." if self.expanded_output else "off."
        return [(None, None, None, message)]

    def toggle_timing(self):
        self.timing_enabled = not self.timing_enabled
        message = "Timing is "
        message += "on." if self.timing_enabled else "off."
        return [(None, None, None, message)]

    def call_pset(self, pattern, **_):
        pattern = pattern.split(" ", 2)
        val = pattern[1] if len(pattern) > 1 else ""
        key = pattern[0]
        if hasattr(self, "pset_" + key):
            return getattr(self, "pset_" + key)(val)
        else:
            return [(None, None, None, "'%s' is currently not supported by pset" % key)]

    def pset_pager(self, value):
        if value == "always":
            self.pager_config = PAGER_ALWAYS
        elif value == "off":
            self.pager_config = PAGER_OFF
        elif value == "on":
            self.pager_config = PAGER_LONG_OUTPUT
        elif self.pager_config == PAGER_LONG_OUTPUT:
            self.pager_config = PAGER_OFF
        else:
            self.pager_config = PAGER_LONG_OUTPUT
        return [(None, None, None, "%s" % PAGER_MSG[self.pager_config])]

    def set_pager(self, pattern, **_):
        if not pattern:
            if not self.pager:
                os.environ.pop("PAGER", None)
                msg = "Pager reset to system default."
            else:
                os.environ["PAGER"] = self.pager
                msg = "Reset pager back to default. Default: %s" % self.pager
        else:
            os.environ["PAGER"] = pattern
            msg = "PAGER set to %s." % pattern

        return [(None, None, None, msg)]


@export
def content_exceeds_width(row, width):
    # Account for 3 characters between each column
    separator_space = len(row) * 3
    # Add 2 columns for a bit of buffer
    line_len = sum([len(x) for x in row]) + separator_space + 2
    return line_len > width


@export
def parse_special_command(sql):
    command, _, arg = sql.partition(" ")
    verbose = "+" in command

    command = command.strip().replace("+", "")
    return (command, verbose, arg.strip())


def show_extra_help_command(command, syntax, description):
    """
    A decorator used internally for registering help for a command that is not
    automatically executed via PGSpecial.execute, but invoked manually by the
    caller (e.g. \watch).
    """

    @special_command(command, syntax, description, arg_type=NO_QUERY)
    def placeholder():
        raise RuntimeError

    def wrapper(wrapped):
        return wrapped

    return wrapper


def special_command(
    command,
    syntax,
    description,
    arg_type=PARSED_QUERY,
    hidden=False,
    case_sensitive=True,
    aliases=(),
):
    """A decorator used internally for static special commands"""

    def wrapper(wrapped):
        register_special_command(
            wrapped,
            command,
            syntax,
            description,
            arg_type,
            hidden,
            case_sensitive,
            aliases,
            command_dict=PGSpecial.default_commands,
        )
        return wrapped

    return wrapper


def register_special_command(
    handler,
    command,
    syntax,
    description,
    arg_type=PARSED_QUERY,
    hidden=False,
    case_sensitive=True,
    aliases=(),
    command_dict=None,
):

    cmd = command.lower() if not case_sensitive else command
    command_dict[cmd] = SpecialCommand(
        handler, syntax, description, arg_type, hidden, case_sensitive
    )
    for alias in aliases:
        cmd = alias.lower() if not case_sensitive else alias
        command_dict[cmd] = SpecialCommand(
            handler,
            syntax,
            description,
            arg_type,
            case_sensitive=case_sensitive,
            hidden=True,
        )


def chunks(l, n):
    n = max(1, n)
    return [l[i : i + n] for i in range(0, len(l), n)]


@special_command(
    "\\e", "\\e [file]", "Edit the query with external editor.", arg_type=NO_QUERY
)
@special_command(
    "\\ef",
    "\\ef [funcname [line]]",
    "Edit the contents of the query buffer.",
    arg_type=NO_QUERY,
    hidden=True,
)
@special_command(
    "\\ev",
    "\\ev [viewname [line]]",
    "Edit the contents of the query buffer.",
    arg_type=NO_QUERY,
    hidden=True,
)
def doc_only():
    "Documention placeholder.  Implemented in pgcli.main.handle_editor_command"
    raise RuntimeError


@special_command(
    "\\do", "\\do[S] [pattern]", "List operators.", arg_type=NO_QUERY, hidden=True
)
@special_command(
    "\\dp",
    "\\dp [pattern]",
    "List table, view, and sequence access privileges.",
    arg_type=NO_QUERY,
    hidden=True,
)
@special_command(
    "\\z", "\\z [pattern]", "Same as \\dp.", arg_type=NO_QUERY, hidden=True
)
def place_holder():
    raise NotImplementedError
