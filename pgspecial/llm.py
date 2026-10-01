import contextlib
import io
import logging
import os
import re
from runpy import run_module
import shlex
import sys
from time import time
from typing import Optional, Tuple
from . import export

import click

try:
    import llm  # type: ignore
    from llm.cli import cli  # type: ignore
except Exception:  # pragma: no cover - llm may not be installed in all envs
    llm = None
    cli = None

from pgspecial.main import parse_special_command, Verbosity

log = logging.getLogger(__name__)


def _safe_models():  # pragma: no cover - used when llm is installed
    try:
        return {x.model_id: None for x in llm.get_models()} if llm else {}
    except Exception:
        return {}


LLM_CLI_COMMANDS = list(cli.commands.keys()) if cli else []
MODELS = _safe_models()
LLM_TEMPLATE_NAME = "pgspecial-llm-template"


def run_external_cmd(cmd, *args, capture_output=False, restart_cli=False, raise_exception=True):
    original_exe = sys.executable
    original_args = sys.argv
    try:
        sys.argv = [cmd] + list(args)
        code = 0
        if capture_output:
            buffer = io.StringIO()
            redirect = contextlib.ExitStack()
            redirect.enter_context(contextlib.redirect_stdout(buffer))
            redirect.enter_context(contextlib.redirect_stderr(buffer))
        else:
            redirect = contextlib.nullcontext()
        with redirect:
            try:
                run_module(cmd, run_name="__main__")
            except SystemExit as e:
                code = e.code
                if code != 0 and raise_exception:
                    if capture_output:
                        raise RuntimeError(buffer.getvalue())
                    else:
                        raise RuntimeError(f"Command {cmd} failed with exit code {code}.")
            except Exception as e:
                code = 1
                if raise_exception:
                    if capture_output:
                        raise RuntimeError(buffer.getvalue())
                    else:
                        raise RuntimeError(f"Command {cmd} failed: {e}")
        if restart_cli and code == 0:
            os.execv(original_exe, [original_exe] + original_args)
        if capture_output:
            return code, buffer.getvalue()
        else:
            return code, ""
    finally:
        sys.argv = original_args


def build_command_tree(cmd):  # pragma: no cover - not used in tests directly
    tree = {}
    if cmd and isinstance(getattr(cmd, "commands", None), dict):
        for name, subcmd in cmd.commands.items():
            if getattr(cmd, "name", None) == "models" and name == "default":
                tree[name] = MODELS
            else:
                tree[name] = build_command_tree(subcmd)
    else:
        tree = None
    return tree


COMMAND_TREE = build_command_tree(cli) if cli else {}


def get_completions(tokens, tree=COMMAND_TREE):  # pragma: no cover - helper
    for token in tokens:
        if token.startswith("-"):
            continue
        if tree and token in tree:
            tree = tree[token]
        else:
            return []
    return list(tree.keys()) if tree else []


@export
class FinishIteration(Exception):
    def __init__(self, results=None):
        self.results = results


USAGE = """
Use an LLM to create SQL queries to answer questions from your database.
Examples:

# Ask a question.
> \\llm 'Most visited urls?'

# List available models
> \\llm models
> gpt-4o
> gpt-3.5-turbo

# Change default model
> \\llm models default llama3

# Set api key (not required for local models)
> \\llm keys set openai

# Install a model plugin
> \\llm install llm-ollama
> llm-ollama installed.

# Plugins directory
# https://llm.datasette.io/en/stable/plugins/directory.html
"""

_SQL_CODE_FENCE = r"```sql\n(.*?)\n```"

PROMPT = """
You are a helpful assistant who is a PostgreSQL expert. You are embedded in a
psql-like cli tool called pgcli.

Answer this question:

$question

Use the following context if it is relevant to answering the question. If the
question is not about the current database then ignore the context.

You are connected to a PostgreSQL database with the following schema:

$db_schema

Here is a sample row of data from each table:

$sample_data

If the answer can be found using a SQL query, include a sql query in a code
fence such as this one:

```sql
SELECT count(*) FROM table_name;
```
Keep your explanation concise and focused on the question asked.
"""


def ensure_pgspecial_template(replace=False):
    if not replace:
        code, _ = run_external_cmd("llm", "templates", "show", LLM_TEMPLATE_NAME, capture_output=True, raise_exception=False)
        if code == 0:
            return
    run_external_cmd("llm", PROMPT, "--save", LLM_TEMPLATE_NAME)
    return


@export
def handle_llm(text, cur) -> Tuple[str, Optional[str], float]:
    _, verbosity, arg = parse_special_command(text)
    if not arg.strip():
        output = USAGE
        raise FinishIteration(output)

    parts = shlex.split(arg)
    restart = False
    if "-c" in parts:
        capture_output = True
        use_context = False
    elif "prompt" in parts:
        capture_output = True
        use_context = True
    elif "install" in parts or "uninstall" in parts:
        capture_output = False
        use_context = False
        restart = True
    elif parts and parts[0] in LLM_CLI_COMMANDS:
        capture_output = False
        use_context = False
    elif parts and parts[0] == "--help":
        capture_output = False
        use_context = False
    else:
        capture_output = True
        use_context = True

    if not use_context:
        args = parts
        if capture_output:
            click.echo("Calling llm command")
            start = time()
            _, result = run_external_cmd("llm", *args, capture_output=capture_output)
            end = time()
            match = re.search(_SQL_CODE_FENCE, result, re.DOTALL)
            if match:
                sql = match.group(1).strip()
            else:
                output = result
                raise FinishIteration(output)
            return (result if verbosity == Verbosity.SUCCINCT else "", sql, end - start)
        else:
            run_external_cmd("llm", *args, restart_cli=restart)
            raise FinishIteration(None)

    try:
        ensure_pgspecial_template()
        start = time()
        context, sql = sql_using_llm(cur=cur, question=arg)
        end = time()
        if verbosity == Verbosity.SUCCINCT:
            context = ""
        return (context, sql, end - start)
    except Exception as e:
        raise RuntimeError(e)


@export
def is_llm_command(command) -> bool:
    cmd, _, _ = parse_special_command(command)
    return cmd in ("\\llm", "\\ai")


def sql_using_llm(cur, question=None) -> Tuple[str, Optional[str]]:
    if cur is None:
        raise RuntimeError("Connect to a database and try again.")

    schema_sql = """
        SELECT
            table_schema,
            table_name,
            string_agg(column_name || ' ' || data_type, ', ' ORDER BY ordinal_position) AS cols
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        GROUP BY table_schema, table_name
        ORDER BY table_schema, table_name
    """
    tables_sql = """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
          AND table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_schema, table_name
    """
    sample_row_tmpl = 'SELECT * FROM "{schema}"."{table}" LIMIT 1'

    click.echo("Preparing schema information to feed the llm")
    cur.execute(schema_sql)
    db_schema = []
    for row in cur.fetchall():
        # Support both tuple results and dict-like rows
        if isinstance(row, (list, tuple)):
            schema, table, cols = row
        else:
            schema, table, cols = row["table_schema"], row["table_name"], row["cols"]
        db_schema.append(f"{schema}.{table}({cols})")
    db_schema = "\n".join(db_schema)

    cur.execute(tables_sql)
    sample_data = {}
    for row in cur.fetchall():
        if isinstance(row, (list, tuple)):
            schema, table = row
        else:
            schema, table = row["table_schema"], row["table_name"]
        try:
            cur.execute(sample_row_tmpl.format(schema=schema, table=table))
        except Exception:
            continue
        cols = [desc[0] for desc in getattr(cur, "description", [])]
        one = getattr(cur, "fetchone", lambda: None)()
        if not one:
            continue
        sample_data[f"{schema}.{table}"] = list(zip(cols, one))

    args = [
        "--template",
        LLM_TEMPLATE_NAME,
        "--param",
        "db_schema",
        db_schema,
        "--param",
        "sample_data",
        sample_data,
        "--param",
        "question",
        question,
        " ",
    ]
    click.echo("Invoking llm command with schema information")
    _, result = run_external_cmd("llm", *args, capture_output=True)
    match = re.search(_SQL_CODE_FENCE, result, re.DOTALL)
    if match:
        sql = match.group(1).strip()
    else:
        sql = ""
    return (result, sql)
