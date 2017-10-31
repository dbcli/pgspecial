  #!/usr/bin/python
  # -*- coding: utf-8 -*-

from dbutils import dbtest, POSTGRES_USER
import itertools

objects_listing_headers = ['Schema', 'Name', 'Type', 'Owner', 'Size', 'Description']


@dbtest
def test_slash_d(executor):
    results = executor('\d')
    title = None
    rows = [('public', 'Inh1', 'table', POSTGRES_USER),
            ('public', 'inh2', 'table', POSTGRES_USER),
            ('public', 'mvw1', 'materialized view', POSTGRES_USER),
            ('public', 'tbl1', 'table', POSTGRES_USER),
            ('public', 'tbl2', 'table', POSTGRES_USER),
            ('public', 'tbl2_id2_seq', 'sequence', POSTGRES_USER),
            ('public', 'tbl3', 'table', POSTGRES_USER),
            ('public', 'vw1', 'view', POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = 'SELECT 8'
    expected = [title, rows, headers, status]

    assert results == expected


@dbtest
def test_slash_d_verbose(executor):
    results = executor('\d+')
    title = None
    rows = [('public', 'Inh1', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'inh2', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'mvw1', 'materialized view',
             POSTGRES_USER, '8192 bytes', None),
            ('public', 'tbl1', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'tbl2', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'tbl2_id2_seq', 'sequence',
             POSTGRES_USER, '8192 bytes', None),
            ('public', 'tbl3', 'table', POSTGRES_USER, '0 bytes', None),
            ('public', 'vw1', 'view', POSTGRES_USER, '0 bytes', None)]
    headers = objects_listing_headers
    status = 'SELECT 8'
    expected = [title, rows, headers, status]

    assert results == expected


@dbtest
def test_slash_d_table_1(executor):
    results = executor('\d tbl1')
    title = None
    rows = [['id1', 'integer', ' not null'],
            ['txt1', 'text', ' not null'],
            ]
    headers = ['Column', 'Type', 'Modifiers']
    status = ('Indexes:\n    "id_text" PRIMARY KEY, btree (id1, txt1)\n'
              'Number of child tables: 2 (Use \\d+ to list them.)\n')
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_2(executor):
    results = executor('\d tbl2')
    title = None
    rows = [['id2', 'integer', " not null default nextval('tbl2_id2_seq'::regclass)"],
            ['txt2', 'text', ''],
            ]
    headers = ['Column', 'Type', 'Modifiers']
    status = ('Number of child tables: 1 (Use \\d+ to list them.)\n')
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_verbose_1(executor):
    title = None
    headers = ['Column', 'Type', 'Modifiers',
               'Storage', 'Stats target', 'Description']

    results = executor('\d+ tbl1')
    rows = [['id1', 'integer', ' not null', 'plain', None, None],
            ['txt1', 'text', ' not null', 'extended', None, None],
            ]
    status = ('Indexes:\n    "id_text" PRIMARY KEY, btree (id1, txt1)\n'
              'Child tables: "Inh1",\n'
              '              inh2\n'
              'Has OIDs: no\n')
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor('\d+ "Inh1"')
    rows = [['id1', 'integer', ' not null', 'plain', None, None],
            ['txt1', 'text', ' not null', 'extended', None, None],
            ['value1', 'integer', '', 'plain', None, None],
            ]
    status = ('Inherits: tbl1\n'
              'Has OIDs: no\n')
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_verbose_2(executor):
    title = None
    headers = ['Column', 'Type', 'Modifiers',
               'Storage', 'Stats target', 'Description']

    results = executor('\d+ tbl2')
    rows = [['id2', 'integer', " not null default nextval('tbl2_id2_seq'::regclass)",
             'plain', None, None],
            ['txt2', 'text', '', 'extended', None, None],
            ]
    status = ('Child tables: inh2\n'
              'Has OIDs: no\n')
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor('\d+ inh2')
    rows = [['id1', 'integer', ' not null', 'plain', None, None],
            ['txt1', 'text', ' not null', 'extended', None, None],
            ['id2', 'integer', " not null default nextval('tbl2_id2_seq'::regclass)",
             'plain', None, None],
            ['txt2', 'text', '', 'extended', None, None],
            ['value2', 'integer', '', 'plain', None, None],
            ]
    status = ('Inherits: tbl1,\n'
              '          tbl2\n'
              'Has OIDs: no\n')
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_d_table_with_exclusion(executor):
    results = executor('\d tbl3')
    title = None
    rows = [['c3', 'circle', '']]
    headers = ['Column', 'Type', 'Modifiers']
    status = 'Indexes:\n    "tbl3_c3_excl" EXCLUDE USING gist (c3 WITH &&)\n'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dn(executor):
    """List all schemas."""
    results = executor('\dn')
    title = None
    rows = [('public', POSTGRES_USER),
            ('schema1', POSTGRES_USER),
            ('schema2', POSTGRES_USER)]
    headers = ['Name', 'Owner']
    status = 'SELECT 3'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dt(executor):
    """List all tables in public schema."""
    results = executor('\dt')
    title = None
    rows = [('public', 'Inh1', 'table', POSTGRES_USER),
            ('public', 'inh2', 'table', POSTGRES_USER),
            ('public', 'tbl1', 'table', POSTGRES_USER),
            ('public', 'tbl2', 'table', POSTGRES_USER),
            ('public', 'tbl3', 'table', POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = 'SELECT 5'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dt_verbose(executor):
    """List all tables in public schema in verbose mode."""
    results = executor('\dt+')
    title = None
    rows = [('public', 'Inh1', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'inh2', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'tbl1', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'tbl2', 'table', POSTGRES_USER, '8192 bytes', None),
            ('public', 'tbl3', 'table', POSTGRES_USER, '0 bytes', None)]
    headers = objects_listing_headers
    status = 'SELECT 5'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dv(executor):
    """List all views in public schema."""
    results = executor('\dv')
    title = None
    row = [('public', 'vw1', 'view', POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = 'SELECT 1'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dv_verbose(executor):
    """List all views in s1 schema in verbose mode."""
    results = executor('\dv+ schema1.*')
    title = None
    row = [('schema1', 's1_vw1', 'view', POSTGRES_USER, '0 bytes', None)]
    headers = objects_listing_headers
    status = 'SELECT 1'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dm(executor):
    """List all materialized views in schema1."""
    results = executor('\dm schema1.*')
    title = None
    row = [('schema1', 's1_mvw1', 'materialized view', POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = 'SELECT 1'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dm_verbose(executor):
    """List all materialized views in public schema in verbose mode."""
    results = executor('\dm+')
    title = None
    row = [('public', 'mvw1', 'materialized view', POSTGRES_USER, '8192 bytes', None)]
    headers = objects_listing_headers
    status = 'SELECT 1'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_ds(executor):
    """List all sequences in public schema."""
    results = executor('\ds')
    title = None
    row = [('public', 'tbl2_id2_seq', 'sequence', POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = 'SELECT 1'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_ds_verbose(executor):
    """List all sequences in public schema in verbose mode."""
    results = executor('\ds+')
    title = None
    row = [('public', 'tbl2_id2_seq', 'sequence', POSTGRES_USER, '8192 bytes', None)]
    headers = objects_listing_headers
    status = 'SELECT 1'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_di(executor):
    """List all indexes in public schema."""
    results = executor('\di')
    title = None
    row = [('public', 'id_text', 'index', POSTGRES_USER),
           ('public', 'tbl3_c3_excl', 'index', POSTGRES_USER)]
    headers = objects_listing_headers[:-2]
    status = 'SELECT 2'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_di_verbose(executor):
    """List all indexes in public schema in verbose mode."""
    results = executor('\di+')
    title = None
    row = [('public', 'id_text', 'index', POSTGRES_USER, '8192 bytes', None),
           ('public', 'tbl3_c3_excl', 'index', POSTGRES_USER, '8192 bytes', None)]
    headers = objects_listing_headers
    status = 'SELECT 2'
    expected = [title, row, headers, status]
    assert results == expected


@dbtest
def test_slash_dT(executor):
    """List all datatypes."""
    results = executor('\dT')
    title = None
    rows = [('public', 'foo', None),
            ('public', 'gender_t', None)]
    headers = ['Schema', 'Name', 'Description']
    status = 'SELECT 2'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dD(executor):
    title = None
    headers = ['Schema', 'Name', 'Type', 'Modifier', 'Check']
    results = executor('\dD')
    rows = [('public', 'gender_t', 'character(1)', '',
             "CHECK (VALUE = ANY (ARRAY['F'::bpchar, 'M'::bpchar]))")]
    status = 'SELECT 1'
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor('\dD schema1.*')
    rows = [('schema1', 'bigint_t', 'bigint', '', ''),
            ('schema1', 'smallint_t', 'smallint', '', '')]
    status = 'SELECT 2'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dD_verbose(executor):
    title = None
    headers = ['Schema', 'Name', 'Type', 'Modifier', 'Check',
               'Access privileges', 'Description']
    results = executor('\dD+')
    rows = [('public', 'gender_t', 'character(1)', '',
             "CHECK (VALUE = ANY (ARRAY['F'::bpchar, 'M'::bpchar]))",
             None, None)]
    status = 'SELECT 1'
    expected = [title, rows, headers, status]
    assert results == expected

    results = executor('\dD+ schema1.bigint_t')
    rows = [('schema1', 'bigint_t', 'bigint', '', '', None,
             'a really large integer')]
    status = 'SELECT 1'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_db(executor):
    """List all tablespaces."""
    title, rows, header, status = executor('\db')
    assert title is None
    assert header == ['Name', 'Owner', 'Location']
    assert 'pg_default' in rows[0]


@dbtest
def test_slash_db_name(executor):
    """List tablespace by name."""
    title, rows, header, status = executor('\db pg_default')
    assert title is None
    assert header == ['Name', 'Owner', 'Location']
    assert 'pg_default' in rows[0]
    assert status == 'SELECT 1'


@dbtest
def test_slash_df(executor):
    results = executor('\df')
    title = None
    rows = [('public', 'func1', 'integer', '', 'normal')]
    headers = ['Schema', 'Name', 'Result data type', 'Argument data types',
            'Type']
    status = 'SELECT 1'
    expected = [title, rows, headers, status]
    assert results == expected

help_rows = [['ABORT', 'ALTER AGGREGATE', 'ALTER COLLATION', 'ALTER CONVERSION', 'ALTER DATABASE', 'ALTER DEFAULT PRIVILEGES'], ['ALTER DOMAIN', 'ALTER EVENT TRIGGER', 'ALTER EXTENSION', 'ALTER FOREIGN DATA WRAPPER', 'ALTER FOREIGN TABLE', 'ALTER FUNCTION'], ['ALTER GROUP', 'ALTER INDEX', 'ALTER LANGUAGE', 'ALTER LARGE OBJECT', 'ALTER MATERIALIZED VIEW', 'ALTER OPCLASS'], ['ALTER OPERATOR', 'ALTER OPFAMILY', 'ALTER POLICY', 'ALTER ROLE', 'ALTER RULE', 'ALTER SCHEMA'], ['ALTER SEQUENCE', 'ALTER SERVER', 'ALTER SYSTEM', 'ALTER TABLE', 'ALTER TABLESPACE', 'ALTER TRIGGER'], ['ALTER TSCONFIG', 'ALTER TSDICTIONARY', 'ALTER TSPARSER', 'ALTER TSTEMPLATE', 'ALTER TYPE', 'ALTER USER'], ['ALTER USER MAPPING', 'ALTER VIEW', 'ANALYZE', 'BEGIN', 'CHECKPOINT', 'CLOSE'], ['CLUSTER', 'COMMENT', 'COMMIT', 'COMMIT PREPARED', 'COPY', 'CREATE AGGREGATE'], ['CREATE CAST', 'CREATE COLLATION', 'CREATE CONVERSION', 'CREATE DATABASE', 'CREATE DOMAIN', 'CREATE EVENT TRIGGER'], ['CREATE EXTENSION', 'CREATE FOREIGN DATA WRAPPER', 'CREATE FOREIGN TABLE', 'CREATE FUNCTION', 'CREATE GROUP', 'CREATE INDEX'], ['CREATE LANGUAGE', 'CREATE MATERIALIZED VIEW', 'CREATE OPCLASS', 'CREATE OPERATOR', 'CREATE OPFAMILY', 'CREATE POLICY'], ['CREATE ROLE', 'CREATE RULE', 'CREATE SCHEMA', 'CREATE SEQUENCE', 'CREATE SERVER', 'CREATE TABLE'], ['CREATE TABLE AS', 'CREATE TABLESPACE', 'CREATE TRANSFORM', 'CREATE TRIGGER', 'CREATE TSCONFIG', 'CREATE TSDICTIONARY'], ['CREATE TSPARSER', 'CREATE TSTEMPLATE', 'CREATE TYPE', 'CREATE USER', 'CREATE USER MAPPING', 'CREATE VIEW'], ['DEALLOCATE', 'DECLARE', 'DELETE', 'DISCARD', 'DO', 'DROP AGGREGATE'], ['DROP CAST', 'DROP COLLATION', 'DROP CONVERSION', 'DROP DATABASE', 'DROP DOMAIN', 'DROP EVENT TRIGGER'], ['DROP EXTENSION', 'DROP FOREIGN DATA WRAPPER', 'DROP FOREIGN TABLE', 'DROP FUNCTION', 'DROP GROUP', 'DROP INDEX'], ['DROP LANGUAGE', 'DROP MATERIALIZED VIEW', 'DROP OPCLASS', 'DROP OPERATOR', 'DROP OPFAMILY', 'DROP OWNED'], ['DROP POLICY', 'DROP ROLE', 'DROP RULE', 'DROP SCHEMA', 'DROP SEQUENCE', 'DROP SERVER'], ['DROP TABLE', 'DROP TABLESPACE', 'DROP TRANSFORM', 'DROP TRIGGER', 'DROP TSCONFIG', 'DROP TSDICTIONARY'], ['DROP TSPARSER', 'DROP TSTEMPLATE', 'DROP TYPE', 'DROP USER', 'DROP USER MAPPING', 'DROP VIEW'], ['END', 'EXECUTE', 'EXPLAIN', 'FETCH', 'GRANT', 'IMPORT FOREIGN SCHEMA'], ['INSERT', 'LISTEN', 'LOAD', 'LOCK', 'MOVE', 'NOTIFY'], ['PGBENCH', 'PREPARE', 'PREPARE TRANSACTION', 'REASSIGN OWNED', 'REFRESH MATERIALIZED VIEW', 'REINDEX'], ['RELEASE SAVEPOINT', 'RESET', 'REVOKE', 'ROLLBACK', 'ROLLBACK PREPARED', 'ROLLBACK TO'], ['SAVEPOINT', 'SECURITY LABEL', 'SELECT', 'SELECT INTO', 'SET', 'SET CONSTRAINTS'], ['SET ROLE', 'SET SESSION AUTH', 'SET TRANSACTION', 'SHOW', 'START TRANSACTION', 'TRUNCATE'], ['UNLISTEN', 'UPDATE', 'VACUUM', 'VALUES']]

@dbtest
def test_slash_h(executor):
    """List all commands."""
    results = executor('\h')
    expected = [None, help_rows, [], None]
    assert results == expected

@dbtest
def test_slash_h_command(executor):
    """Check help is returned for all commands"""
    for command in itertools.chain(*help_rows):
        results = executor('\h %s' % command)
        assert results[3].startswith('Description\n')
        assert 'Syntax' in results[3]

@dbtest
def test_slash_h_alias(executor):
    """\? is properly aliased to \h"""
    h_results = executor('\h SELECT')
    results = executor('\? SELECT')
    assert results[3] == h_results[3]


@dbtest
def test_slash_copy_to_tsv(executor, tmpdir):
    filepath = tmpdir.join('pycons.tsv')
    executor(u"\copy (SELECT 'Montréal', 'Portland', 'Cleveland') TO '{0}' "
             .format(filepath))
    infile = filepath.open(encoding='utf-8')
    contents = infile.read()
    assert len(contents.splitlines()) == 1
    assert u'Montréal' in contents


@dbtest
def test_slash_copy_to_stdout(executor, capsys):
    executor(u"\copy (SELECT 'Montréal', 'Portland', 'Cleveland') TO stdout")
    (out, err) = capsys.readouterr()
    assert out == u'Montréal\tPortland\tCleveland\n'


@dbtest
def test_slash_copy_to_csv(executor, tmpdir):
    filepath = tmpdir.join('pycons.tsv')
    executor(u"\copy (SELECT 'Montréal', 'Portland', 'Cleveland') TO '{0}' WITH csv"
             .format(filepath))
    infile = filepath.open(encoding='utf-8')
    contents = infile.read()
    assert len(contents.splitlines()) == 1
    assert u'Montréal' in contents
    assert u',' in contents


@dbtest
def test_slash_copy_from_csv(executor, connection, tmpdir):
    filepath = tmpdir.join('tbl1.csv')
    executor("\copy (SELECT 22, 'elephant') TO '{0}' WITH csv"
             .format(filepath))
    executor("\copy tbl1 FROM '{0}' WITH csv".format(filepath))
    cur = connection.cursor()
    cur.execute("SELECT * FROM tbl1 WHERE id1 = 22")
    row = cur.fetchone()
    assert row[1] == 'elephant'


@dbtest
def test_slash_sf(executor):
    results = executor('\sf func1')
    title = None
    rows = [('CREATE OR REPLACE FUNCTION public.func1()\n'
             ' RETURNS integer\n'
             ' LANGUAGE sql\n'
             'AS $function$select 1$function$\n',),
            ]
    headers = ['source']
    status = None
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_sf_unknown(executor):
    try:
        executor('\sf non_existing')
    except Exception as e:
        assert 'non_existing' in str(e)
    else:
        assert False, "Expected an exception"


@dbtest
def test_slash_sf_parens(executor):
    results = executor('\sf func1()')
    title = None
    rows = [('CREATE OR REPLACE FUNCTION public.func1()\n'
             ' RETURNS integer\n'
             ' LANGUAGE sql\n'
             'AS $function$select 1$function$\n',),
            ]
    headers = ['source']
    status = None
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_sf_verbose(executor):
    results = executor('\sf+ schema1.s1_func1')
    title = None
    rows = [('        CREATE OR REPLACE FUNCTION schema1.s1_func1()\n'
             '         RETURNS integer\n'
             '         LANGUAGE sql\n'
             '1       AS $function$select 2$function$\n',),
            ]
    headers = ['source']
    status = None
    expected = [title, rows, headers, status]
    assert results == expected
