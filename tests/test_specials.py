#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytest
from dbutils import dbtest, POSTGRES_USER, SERVER_VERSION, foreign_db_environ, fdw_test
import itertools
import locale

objects_listing_headers = ["Schema", "Name", "Type", "Owner", "Size", "Description"]

# note: technically, this is the database encoding, not the client
# locale but for the purpose of testing we can assume the server
# and the client are using the same locale
# note 2: locale.getlocale() does not return the raw values,
# in particular it transforms C into en_US, so we use .setlocale()
# instead as that matches the C library function
LC_COLLATE = locale.setlocale(locale.LC_COLLATE, None)
LC_CTYPE = locale.setlocale(locale.LC_CTYPE, None)


@dbtest
def test_slash_l(executor):
    results = executor(r"\l")
    row = ("_test_db", "postgres", "UTF8", LC_COLLATE, LC_CTYPE, None)
    headers = ["Name", "Owner", "Encoding", "Collate", "Ctype", "Access privileges"]
    assert row in results[1]
    assert headers == results[2]


@dbtest
def test_slash_l_pattern(executor):
    results = executor(r"\l _test*")
    row = [("_test_db", "postgres", "UTF8", LC_COLLATE, LC_CTYPE, None)]
    headers = ["Name", "Owner", "Encoding", "Collate", "Ctype", "Access privileges"]
    assert row == results[1]
    assert headers == results[2]


@dbtest
def test_slash_l_verbose(executor):
    results = executor(r"\l+")
    headers = [
        "Name",
        "Owner",
        "Encoding",
        "Collate",
        "Ctype",
        "Access privileges",
        "Size",
        "Tablespace",
        "Description",
    ]
    assert headers == results[2]


@dbtest
def test_slash_du(executor):
    results = executor(r"\du")
    row = ("postgres", True, True, True, True, True, -1, None, [], True)
    headers = [
        "rolname",
        "rolsuper",
        "rolinherit",
        "rolcreaterole",
        "rolcreatedb",
        "rolcanlogin",
        "rolconnlimit",
        "rolvaliduntil",
        "memberof",
        "rolreplication",
    ]
    assert headers == results[2]
    assert row in results[1]


@dbtest
def test_slash_du_pattern(executor):
    results = executor(r"\du post*")
    row = [("postgres", True, True, True, True, True, -1, None, [], True)]
    headers = [
        "rolname",
        "rolsuper",
        "rolinherit",
        "rolcreaterole",
        "rolcreatedb",
        "rolcanlogin",
        "rolconnlimit",
        "rolvaliduntil",
        "memberof",
        "rolreplication",
    ]
    assert headers == results[2]
    assert row == results[1]


@dbtest
def test_slash_du_verbose(executor):
    results = executor(r"\du+")
    row = ("postgres", True, True, True, True, True, -1, None, [], None, True)
    headers = [
        "rolname",
        "rolsuper",
        "rolinherit",
        "rolcreaterole",
        "rolcreatedb",
        "rolcanlogin",
        "rolconnlimit",
        "rolvaliduntil",
        "memberof",
        "description",
        "rolreplication",
    ]
    assert headers == results[2]
    assert row in results[1]


@dbtest
def test_slash_d(executor):
    results = executor(r"\d")
    title = None
    rows = [
        ("public", "Inh1", "table", POSTGRES_USER),
        ("public", "inh2", "table", POSTGRES_USER),
        ("public", "mvw1", "materialized view", POSTGRES_USER),
        ("public", "tbl1", "table", POSTGRES_USER),
        ("public", "tbl2", "table", POSTGRES_USER),
        ("public", "tbl2_id2_seq", "sequence", POSTGRES_USER),
        ("public", "tbl3", "table", POSTGRES_USER),
        ("public", "vw1", "view", POSTGRES_USER),
    ]
    headers = objects_listing_headers[:-2]
    status = "SELECT 8"
    expected = [title, rows, headers, status]

    assert results == expected


@dbtest
def test_slash_d_verbose(executor):
    results = executor(r"\d+")
    title = None
    rows = [
        ("public", "Inh1", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "inh2", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "mvw1", "materialized view", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl1", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl2", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl2_id2_seq", "sequence", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl3", "table", POSTGRES_USER, "0 bytes", None),
        ("public", "vw1", "view", POSTGRES_USER, "0 bytes", None),
    ]
    headers = objects_listing_headers
    status = "SELECT 8"
    expected = [title, rows, headers, status]

    assert results == expected


@dbtest
def test_slash_d_table_1(executor):
    results = executor(r"\d tbl1")
    title = None
    rows = [
        ["id1", "integer", " not null"],
        ["txt1", "text", " not null"],
    ]
    headers = ["Column", "Type", "Modifiers"]
    status = 'Indexes:\n    "id_text" PRIMARY KEY, btree (id1, txt1)\nNumber of child tables: 2 (Use \\d+ to list them.)\n'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_2(executor):
    results = executor(r"\d tbl2")
    title = None
    rows = [
        ["id2", "integer", " not null default nextval('tbl2_id2_seq'::regclass)"],
        ["txt2", "text", ""],
    ]
    headers = ["Column", "Type", "Modifiers"]
    status = "Number of child tables: 1 (Use \\d+ to list them.)\n"
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_test_generated_default(executor):
    results = executor(r"\d schema3.test_generated_default")
    headers = ["Column", "Type", "Modifiers"]
    status = 'Indexes:\n    "test_generated_default_pkey" PRIMARY KEY, btree (id)\n'
    rows = [
        ["id", "integer", " not null generated by default as identity"],
        ["some_stuff", "text", ""],
    ]
    assert rows == results[1]
    assert headers == results[2]
    assert status == results[3]


@dbtest
def test_slash_d_table_verbose_1(executor):
    title = None
    headers = ["Column", "Type", "Modifiers", "Storage", "Stats target", "Description"]

    results = executor(r"\d+ tbl1")
    rows = [
        ["id1", "integer", " not null", "plain", None, None],
        ["txt1", "text", " not null", "extended", None, None],
    ]
    status = 'Indexes:\n    "id_text" PRIMARY KEY, btree (id1, txt1)\nChild tables: "Inh1",\n              inh2\nHas OIDs: no\n'
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor(r'\d+ "Inh1"')
    rows = [
        ["id1", "integer", " not null", "plain", None, None],
        ["txt1", "text", " not null", "extended", None, None],
        ["value1", "integer", "", "plain", None, None],
    ]
    status = "Inherits: tbl1\nHas OIDs: no\n"
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_verbose_2(executor):
    title = None
    headers = ["Column", "Type", "Modifiers", "Storage", "Stats target", "Description"]

    results = executor(r"\d+ tbl2")
    rows = [
        [
            "id2",
            "integer",
            " not null default nextval('tbl2_id2_seq'::regclass)",
            "plain",
            None,
            None,
        ],
        ["txt2", "text", "", "extended", None, None],
    ]
    status = "Child tables: inh2\nHas OIDs: no\n"
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor(r"\d+ inh2")
    rows = [
        ["id1", "integer", " not null", "plain", None, None],
        ["txt1", "text", " not null", "extended", None, None],
        [
            "id2",
            "integer",
            " not null default nextval('tbl2_id2_seq'::regclass)",
            "plain",
            None,
            None,
        ],
        ["txt2", "text", "", "extended", None, None],
        ["value2", "integer", "", "plain", None, None],
    ]
    status = "Inherits: tbl1,\n          tbl2\nHas OIDs: no\n"
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_view_verbose(executor):
    title = None
    headers = ["Column", "Type", "Modifiers", "Storage", "Description"]

    results = executor(r"\d+ vw1")
    rows = [
        ["id1", "integer", "", "plain", None],
        ["txt1", "text", "", "extended", None],
    ]
    status = "View definition:\n SELECT tbl1.id1,\n    tbl1.txt1\n   FROM tbl1; \n"

    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_with_exclusion(executor):
    results = executor(r"\d tbl3")
    title = None
    rows = [["c3", "circle", ""]]
    headers = ["Column", "Type", "Modifiers"]
    status = 'Indexes:\n    "tbl3_c3_excl" EXCLUDE USING gist (c3 WITH &&)\n'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_2_in_schema(executor):
    results = executor(r"\d schema2.tbl2")
    title = None
    rows = [
        [
            "id2",
            "integer",
            " not null default nextval('schema2.tbl2_id2_seq'::regclass)",
        ],
        ["txt2", "text", ""],
    ]
    headers = ["Column", "Type", "Modifiers"]
    status = ""
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dn(executor):
    """List all schemas."""
    results = executor(r"\dn")
    title = None
    if SERVER_VERSION >= 150001:
        rows = [
            ("public", "pg_database_owner"),
            ("schema1", POSTGRES_USER),
            ("schema2", POSTGRES_USER),
            ("schema3", POSTGRES_USER),
        ]
    else:
        rows = [
            ("public", POSTGRES_USER),
            ("schema1", POSTGRES_USER),
            ("schema2", POSTGRES_USER),
            ("schema3", POSTGRES_USER),
        ]

    headers = ["Name", "Owner"]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dp(executor):
    """List all schemas."""
    results = executor(r"\dp")
    title = None
    rows = [
        ("public", "Inh1", "table", None, "", ""),
        ("public", "inh2", "table", None, "", ""),
        ("public", "mvw1", "materialized view", None, "", ""),
        ("public", "tbl1", "table", None, "", ""),
        ("public", "tbl2", "table", None, "", ""),
        ("public", "tbl2_id2_seq", "sequence", None, "", ""),
        ("public", "tbl3", "table", None, "", ""),
        ("public", "vw1", "view", None, "", ""),
    ]

    headers = [
        "Schema",
        "Name",
        "Type",
        "Access privileges",
        "Column privileges",
        "Policies",
    ]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dp_pattern_table(executor):
    """List all schemas."""
    results = executor(r"\dp i*2")
    title = None
    rows = [("public", "inh2", "table", None, "", "")]
    headers = [
        "Schema",
        "Name",
        "Type",
        "Access privileges",
        "Column privileges",
        "Policies",
    ]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dp_pattern_schema(executor):
    """List all schemas."""
    results = executor(r"\dp schema2.*")
    title = None
    rows = [
        ("schema2", "tbl2", "table", None, "", ""),
        ("schema2", "tbl2_id2_seq", "sequence", None, "", ""),
    ]
    headers = [
        "Schema",
        "Name",
        "Type",
        "Access privileges",
        "Column privileges",
        "Policies",
    ]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dp_pattern_alias(executor):
    """List all schemas."""
    results = executor(r"\z i*2")
    title = None
    rows = [("public", "inh2", "table", None, "", "")]
    headers = [
        "Schema",
        "Name",
        "Type",
        "Access privileges",
        "Column privileges",
        "Policies",
    ]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_ddp(executor):
    """List all schemas."""
    results = executor(r"\ddp")
    title = None
    rows = [
        ("postgres", "schema1", "table", "test_role=r/postgres"),
        ("postgres", "schema2", "table", "test_role=arwdDxt/postgres"),
    ]

    headers = [
        "Owner",
        "Schema",
        "Type",
        "Access privileges",
    ]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_ddp_pattern(executor):
    """List all schemas."""
    results = executor(r"\ddp schema2")
    title = None
    rows = [("postgres", "schema2", "table", "test_role=arwdDxt/postgres")]
    headers = [
        "Owner",
        "Schema",
        "Type",
        "Access privileges",
    ]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dt(executor):
    """List all tables in public schema."""
    results = executor(r"\dt")
    title = None
    rows = [
        ("public", "Inh1", "table", POSTGRES_USER),
        ("public", "inh2", "table", POSTGRES_USER),
        ("public", "tbl1", "table", POSTGRES_USER),
        ("public", "tbl2", "table", POSTGRES_USER),
        ("public", "tbl3", "table", POSTGRES_USER),
    ]
    headers = objects_listing_headers[:-2]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dt_verbose(executor):
    """List all tables in public schema in verbose mode."""
    results = executor(r"\dt+")
    title = None
    rows = [
        ("public", "Inh1", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "inh2", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl1", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl2", "table", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl3", "table", POSTGRES_USER, "0 bytes", None),
    ]
    headers = objects_listing_headers
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dv(executor):
    """List all views in public schema."""
    results = executor(r"\dv")
    title = None
    row = [("public", "vw1", "view", POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = "SELECT 1"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dv_verbose(executor):
    """List all views in s1 schema in verbose mode."""
    results = executor(r"\dv+ schema1.*")
    title = None
    row = [("schema1", "s1_vw1", "view", POSTGRES_USER, "0 bytes", None)]
    headers = objects_listing_headers
    status = "SELECT 1"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dm(executor):
    """List all materialized views in schema1."""
    results = executor(r"\dm schema1.*")
    title = None
    row = [("schema1", "s1_mvw1", "materialized view", POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = "SELECT 1"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dm_verbose(executor):
    """List all materialized views in public schema in verbose mode."""
    results = executor(r"\dm+")
    title = None
    row = [("public", "mvw1", "materialized view", POSTGRES_USER, "8192 bytes", None)]
    headers = objects_listing_headers
    status = "SELECT 1"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_ds(executor):
    """List all sequences in public schema."""
    results = executor(r"\ds")
    title = None
    row = [("public", "tbl2_id2_seq", "sequence", POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = "SELECT 1"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_ds_verbose(executor):
    """List all sequences in public schema in verbose mode."""
    results = executor(r"\ds+")
    title = None
    row = [("public", "tbl2_id2_seq", "sequence", POSTGRES_USER, "8192 bytes", None)]
    headers = objects_listing_headers
    status = "SELECT 1"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_di(executor):
    """List all indexes in public schema."""
    results = executor(r"\di")
    title = None
    row = [
        ("public", "id_text", "index", POSTGRES_USER),
        ("public", "tbl3_c3_excl", "index", POSTGRES_USER),
    ]
    headers = objects_listing_headers[:-2]
    status = "SELECT %s" % len(row)
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_di_verbose(executor):
    """List all indexes in public schema in verbose mode."""
    results = executor(r"\di+")
    title = None
    row = [
        ("public", "id_text", "index", POSTGRES_USER, "8192 bytes", None),
        ("public", "tbl3_c3_excl", "index", POSTGRES_USER, "8192 bytes", None),
    ]
    headers = objects_listing_headers
    status = "SELECT 2"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dx(executor):
    """List all extensions."""
    results = executor(r"\dx")
    title = None
    row = [("plpgsql", "1.0", "pg_catalog", "PL/pgSQL procedural language")]
    headers = ["Name", "Version", "Schema", "Description"]
    status = "SELECT 1"
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dx_verbose(executor):
    """List all extensions in verbose mode."""
    results = executor(r"\dx+")
    title = '\nObjects in extension "plpgsql"'
    row = [
        ("function plpgsql_call_handler()",),
        ("function plpgsql_inline_handler(internal)",),
        ("function plpgsql_validator(oid)",),
        ("language plpgsql",),
    ]
    headers = ["Object description"]
    status = "SELECT %s" % len(row)
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dT(executor):
    """List all datatypes."""
    results = executor(r"\dT")
    title = None
    rows = [("public", "foo", None), ("public", "gender_t", None)]
    headers = ["Schema", "Name", "Description"]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dD(executor):
    title = None
    headers = ["Schema", "Name", "Type", "Modifier", "Check"]
    results = executor(r"\dD")
    rows = [
        (
            "public",
            "gender_t",
            "character(1)",
            "",
            "CHECK (VALUE = ANY (ARRAY['F'::bpchar, 'M'::bpchar]))",
        )
    ]
    status = "SELECT 1"
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor(r"\dD schema1.*")
    rows = [
        ("schema1", "bigint_t", "bigint", "", ""),
        ("schema1", "smallint_t", "smallint", "", ""),
    ]
    status = "SELECT %s" % len(rows)
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dD_verbose(executor):
    title = None
    headers = [
        "Schema",
        "Name",
        "Type",
        "Modifier",
        "Check",
        "Access privileges",
        "Description",
    ]
    results = executor(r"\dD+")
    rows = [
        (
            "public",
            "gender_t",
            "character(1)",
            "",
            "CHECK (VALUE = ANY (ARRAY['F'::bpchar, 'M'::bpchar]))",
            None,
            None,
        )
    ]
    status = "SELECT 1"
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor(r"\dD+ schema1.bigint_t")
    rows = [("schema1", "bigint_t", "bigint", "", "", None, "a really large integer")]
    status = "SELECT 1"
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dF(executor):
    title, rows, header, status = executor(r"\dF")
    assert title is None
    assert header == ["Schema", "Name", "Description"]
    assert ("pg_catalog", "spanish", "configuration for spanish language") in rows

    _ = executor(r"\dD *ian")
    assert title is None
    assert header == ["Schema", "Name", "Description"]
    assert ("pg_catalog", "russian", "configuration for russian language") in rows

    _ = executor(r"\dD ge*")
    assert title is None
    assert header == ["Schema", "Name", "Description"]
    assert ("pg_catalog", "german", "configuration for german language") in rows


@dbtest
def test_slash_dF_verbose(executor):
    results = executor(r"\dF+")[1]
    assert ("asciihword", "simple") in results

    results = executor(r"\dF+ *panish")[1]
    assert ("asciihword", "spanish_stem") in results

    results = executor(r"\dF+ swed*")[1]
    assert ("asciihword", "swedish_stem") in results

    results = executor(r"\dF+ jap")
    assert results == [None, None, None, 'Did not find any results for pattern "jap".']


@dbtest
def test_slash_db(executor):
    """List all tablespaces."""
    title, rows, header, status = executor(r"\db")
    assert title is None
    assert header == ["Name", "Owner", "Location"]
    assert "pg_default" in rows[0]


@dbtest
def test_slash_db_name(executor):
    """List tablespace by name."""
    title, rows, header, status = executor(r"\db pg_default")
    assert title is None
    assert header == ["Name", "Owner", "Location"]
    assert "pg_default" in rows[0]
    assert status == "SELECT 1"


@dbtest
def test_slash_df(executor):
    results = executor(r"\df")
    title = None
    rows = [("public", "func1", "integer", "", "normal")]
    headers = ["Schema", "Name", "Result data type", "Argument data types", "Type"]
    status = "SELECT 1"
    expected = [title, rows, headers, status]
    assert results == expected


help_rows = [
    [
        "ABORT",
        "ALTER AGGREGATE",
        "ALTER COLLATION",
        "ALTER CONVERSION",
        "ALTER DATABASE",
        "ALTER DEFAULT PRIVILEGES",
    ],
    [
        "ALTER DOMAIN",
        "ALTER EVENT TRIGGER",
        "ALTER EXTENSION",
        "ALTER FOREIGN DATA WRAPPER",
        "ALTER FOREIGN TABLE",
        "ALTER FUNCTION",
    ],
    [
        "ALTER GROUP",
        "ALTER INDEX",
        "ALTER LANGUAGE",
        "ALTER LARGE OBJECT",
        "ALTER MATERIALIZED VIEW",
        "ALTER OPCLASS",
    ],
    [
        "ALTER OPERATOR",
        "ALTER OPFAMILY",
        "ALTER POLICY",
        "ALTER ROLE",
        "ALTER RULE",
        "ALTER SCHEMA",
    ],
    [
        "ALTER SEQUENCE",
        "ALTER SERVER",
        "ALTER SYSTEM",
        "ALTER TABLE",
        "ALTER TABLESPACE",
        "ALTER TRIGGER",
    ],
    [
        "ALTER TSCONFIG",
        "ALTER TSDICTIONARY",
        "ALTER TSPARSER",
        "ALTER TSTEMPLATE",
        "ALTER TYPE",
        "ALTER USER",
    ],
    ["ALTER USER MAPPING", "ALTER VIEW", "ANALYZE", "BEGIN", "CHECKPOINT", "CLOSE"],
    ["CLUSTER", "COMMENT", "COMMIT", "COMMIT PREPARED", "COPY", "CREATE AGGREGATE"],
    [
        "CREATE CAST",
        "CREATE COLLATION",
        "CREATE CONVERSION",
        "CREATE DATABASE",
        "CREATE DOMAIN",
        "CREATE EVENT TRIGGER",
    ],
    [
        "CREATE EXTENSION",
        "CREATE FOREIGN DATA WRAPPER",
        "CREATE FOREIGN TABLE",
        "CREATE FUNCTION",
        "CREATE GROUP",
        "CREATE INDEX",
    ],
    [
        "CREATE LANGUAGE",
        "CREATE MATERIALIZED VIEW",
        "CREATE OPCLASS",
        "CREATE OPERATOR",
        "CREATE OPFAMILY",
        "CREATE POLICY",
    ],
    [
        "CREATE ROLE",
        "CREATE RULE",
        "CREATE SCHEMA",
        "CREATE SEQUENCE",
        "CREATE SERVER",
        "CREATE TABLE",
    ],
    [
        "CREATE TABLE AS",
        "CREATE TABLESPACE",
        "CREATE TRANSFORM",
        "CREATE TRIGGER",
        "CREATE TSCONFIG",
        "CREATE TSDICTIONARY",
    ],
    [
        "CREATE TSPARSER",
        "CREATE TSTEMPLATE",
        "CREATE TYPE",
        "CREATE USER",
        "CREATE USER MAPPING",
        "CREATE VIEW",
    ],
    ["DEALLOCATE", "DECLARE", "DELETE", "DISCARD", "DO", "DROP AGGREGATE"],
    [
        "DROP CAST",
        "DROP COLLATION",
        "DROP CONVERSION",
        "DROP DATABASE",
        "DROP DOMAIN",
        "DROP EVENT TRIGGER",
    ],
    [
        "DROP EXTENSION",
        "DROP FOREIGN DATA WRAPPER",
        "DROP FOREIGN TABLE",
        "DROP FUNCTION",
        "DROP GROUP",
        "DROP INDEX",
    ],
    [
        "DROP LANGUAGE",
        "DROP MATERIALIZED VIEW",
        "DROP OPCLASS",
        "DROP OPERATOR",
        "DROP OPFAMILY",
        "DROP OWNED",
    ],
    [
        "DROP POLICY",
        "DROP ROLE",
        "DROP RULE",
        "DROP SCHEMA",
        "DROP SEQUENCE",
        "DROP SERVER",
    ],
    [
        "DROP TABLE",
        "DROP TABLESPACE",
        "DROP TRANSFORM",
        "DROP TRIGGER",
        "DROP TSCONFIG",
        "DROP TSDICTIONARY",
    ],
    [
        "DROP TSPARSER",
        "DROP TSTEMPLATE",
        "DROP TYPE",
        "DROP USER",
        "DROP USER MAPPING",
        "DROP VIEW",
    ],
    ["END", "EXECUTE", "EXPLAIN", "FETCH", "GRANT", "IMPORT FOREIGN SCHEMA"],
    ["INSERT", "LISTEN", "LOAD", "LOCK", "MOVE", "NOTIFY"],
    [
        "PGBENCH",
        "PREPARE",
        "PREPARE TRANSACTION",
        "REASSIGN OWNED",
        "REFRESH MATERIALIZED VIEW",
        "REINDEX",
    ],
    [
        "RELEASE SAVEPOINT",
        "RESET",
        "REVOKE",
        "ROLLBACK",
        "ROLLBACK PREPARED",
        "ROLLBACK TO",
    ],
    ["SAVEPOINT", "SECURITY LABEL", "SELECT", "SELECT INTO", "SET", "SET CONSTRAINTS"],
    [
        "SET ROLE",
        "SET SESSION AUTH",
        "SET TRANSACTION",
        "SHOW",
        "START TRANSACTION",
        "TRUNCATE",
    ],
    ["UNLISTEN", "UPDATE", "VACUUM", "VALUES"],
]


@dbtest
def test_slash_h(executor):
    """List all commands."""
    results = executor(r"\h")
    expected = [None, help_rows, [], None]
    assert results == expected


@dbtest
def test_slash_h_command(executor):
    """Check help is returned for all commands"""
    for command in itertools.chain(*help_rows):
        results = executor(r"\h %s" % command)
        assert results[3].startswith("Description\n")
        assert "Syntax" in results[3]


@dbtest
def test_slash_h_alias(executor):
    r"""\? is properly aliased to \h"""
    h_results = executor(r"\h SELECT")
    results = executor(r"\? SELECT")
    assert results[3] == h_results[3]


@dbtest
def test_slash_copy_to_tsv(executor, tmpdir):
    filepath = tmpdir.join("pycons.tsv")
    executor(r"\copy (SELECT 'Montréal', 'Portland', 'Cleveland') TO '{0}' ".format(filepath))
    infile = filepath.open(encoding="utf-8")
    contents = infile.read()
    assert len(contents.splitlines()) == 1
    assert "Montréal" in contents


@dbtest
def test_slash_copy_throws_error_without_TO_or_FROM(executor):
    with pytest.raises(Exception) as exc_info:
        executor("\copy (SELECT 'Montréal', 'Portland', 'Cleveland') INTO stdout ")
    assert str(exc_info.value) == "Missing keyword in \\copy command. Either TO or FROM is required."


@dbtest
def test_slash_copy_to_stdout(executor, capsys):
    executor(r"\copy (SELECT 'Montréal', 'Portland', 'Cleveland') TO stdout")
    (out, err) = capsys.readouterr()
    assert out == "Montréal\tPortland\tCleveland\n"


@dbtest
def test_slash_copy_to_csv(executor, tmpdir):
    filepath = tmpdir.join("pycons.tsv")
    executor(r"\copy (SELECT 'Montréal', 'Portland', 'Cleveland') TO '{0}' WITH csv".format(filepath))
    infile = filepath.open(encoding="utf-8")
    contents = infile.read()
    assert len(contents.splitlines()) == 1
    assert "Montréal" in contents
    assert "," in contents


@dbtest
def test_slash_copy_from_csv(executor, connection, tmpdir):
    filepath = tmpdir.join("tbl1.csv")
    executor(r"\copy (SELECT 22, 'elephant') TO '{0}' WITH csv".format(filepath))
    executor(r"\copy tbl1 FROM '{0}' WITH csv".format(filepath))
    cur = connection.cursor()
    cur.execute("SELECT * FROM tbl1 WHERE id1 = 22")
    row = cur.fetchone()
    assert row[1] == "elephant"


@dbtest
def test_slash_copy_case_insensitive(executor, tmpdir):
    filepath = tmpdir.join("pycons.tsv")
    executor(r"\COPY (SELECT 'Montréal', 'Portland', 'Cleveland') TO '{0}' ".format(filepath))
    infile = filepath.open(encoding="utf-8")
    contents = infile.read()
    assert len(contents.splitlines()) == 1
    assert "Montréal" in contents


@dbtest
def test_slash_sf(executor):
    results = executor(r"\sf func1")
    title = None
    rows = [
        ("CREATE OR REPLACE FUNCTION public.func1()\n RETURNS integer\n LANGUAGE sql\nAS $function$select 1$function$\n",),
    ]
    headers = ["Source"]
    status = None
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_sf_unknown(executor):
    try:
        executor(r"\sf non_existing")
    except Exception as e:
        assert "non_existing" in str(e)
    else:
        assert False, "Expected an exception"


@dbtest
def test_slash_sf_parens(executor):
    results = executor(r"\sf func1()")
    title = None
    rows = [
        ("CREATE OR REPLACE FUNCTION public.func1()\n RETURNS integer\n LANGUAGE sql\nAS $function$select 1$function$\n",),
    ]
    headers = ["Source"]
    status = None
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_sf_verbose(executor):
    results = executor(r"\sf+ schema1.s1_func1")
    title = None
    rows = [
        (
            "        CREATE OR REPLACE FUNCTION schema1.s1_func1()\n"
            "         RETURNS integer\n"
            "         LANGUAGE sql\n"
            "1       AS $function$select 2$function$\n",
        ),
    ]
    headers = ["Source"]
    status = None
    expected = [title, rows, headers, status]
    assert results == expected


@fdw_test
def test_slash_dE(executor):
    with foreign_db_environ():
        results = executor(r"\dE")
        title = None
        rows = [("public", "foreign_foo", "foreign table", "postgres")]
        headers = ["Schema", "Name", "Type", "Owner"]
        status = "SELECT 1"
        expected = [title, rows, headers, status]
        assert results == expected


@fdw_test
def test_slash_dE_with_pattern(executor):
    with foreign_db_environ():
        results = executor(r"\dE foreign_foo")
        title = None
        rows = [("public", "foreign_foo", "foreign table", "postgres")]
        headers = ["Schema", "Name", "Type", "Owner"]
        status = "SELECT 1"
        expected = [title, rows, headers, status]
        assert results == expected

        results = executor(r"\dE *_foo")
        assert results == expected

        results = executor(r"\dE no_such_table")
        rows = []
        status = "SELECT 0"
        expected = [title, rows, headers, status]
        assert results == expected


@fdw_test
def test_slash_dE_verbose(executor):
    with foreign_db_environ():
        results = executor(r"\dE+")
        title = None
        rows = [("public", "foreign_foo", "foreign table", "postgres", "0 bytes", None)]
        headers = ["Schema", "Name", "Type", "Owner", "Size", "Description"]
        status = "SELECT 1"
        expected = [title, rows, headers, status]
        assert results == expected
