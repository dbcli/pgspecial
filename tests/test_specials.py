  #!/usr/bin/python
  # -*- coding: utf-8 -*-

from dbutils import dbtest, POSTGRES_USER
import itertools
from codecs import open


@dbtest
def test_slash_d(executor):
    results = executor('\d')
    title = None
    rows = [('public', 'tbl1', 'table', POSTGRES_USER),
            ('public', 'tbl2', 'table', POSTGRES_USER),
            ('public', 'vw1', 'view', POSTGRES_USER)]
    headers = ['Schema', 'Name', 'Type', 'Owner']
    status = 'SELECT 3'
    expected = [title, rows, headers, status]

    assert results == expected


@dbtest
def test_slash_d_table(executor):
    results = executor('\d tbl1')
    title = None
    rows = [['id1', 'integer', ' not null'],
            ['txt1', 'text', ' not null'],
            ]
    headers = ['Column', 'Type', 'Modifiers']
    status = 'Indexes:\n    "id_text" PRIMARY KEY, btree (id1, txt1)\n'
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
    rows = [('public', 'tbl1', 'table', POSTGRES_USER),
            ('public', 'tbl2', 'table', POSTGRES_USER)]
    headers = ['Schema', 'Name', 'Type', 'Owner']
    status = 'SELECT 2'
    expected = [title, rows, headers, status]
    assert results == expected


@dbtest
def test_slash_dT(executor):
    """List all datatypes."""
    results = executor('\dT')
    title = None
    rows = [('public', 'foo', None)]
    headers = ['Schema', 'Name', 'Description']
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
    infile =filepath.open(encoding='utf-8')
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
