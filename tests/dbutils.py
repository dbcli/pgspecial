import pytest
import psycopg2
import psycopg2.extras


# TODO: should this be somehow be divined from environment?
POSTGRES_USER, POSTGRES_HOST = 'postgres', 'localhost'


def db_connection(dbname=None):
    conn = psycopg2.connect(user=POSTGRES_USER, host=POSTGRES_HOST,
        database=dbname)
    conn.autocommit = True
    return conn


try:
    conn = db_connection()
    CAN_CONNECT_TO_DB = True
    SERVER_VERSION = conn.server_version
except:
    CAN_CONNECT_TO_DB = False
    SERVER_VERSION = 0


dbtest = pytest.mark.skipif(
    not CAN_CONNECT_TO_DB,
    reason="Need a postgres instance at localhost accessible by user "
           "'%s'" % POSTGRES_USER)


def create_db(dbname):
    with db_connection().cursor() as cur:
        try:
            cur.execute('''CREATE DATABASE _test_db''')
        except:
            pass


def setup_db(conn):
    with conn.cursor() as cur:
        # schemas
        cur.execute('create schema schema1')
        cur.execute('create schema schema2')

        # tables
        cur.execute('create table tbl1(id1 integer, txt1 text, CONSTRAINT id_text PRIMARY KEY(id1, txt1))')
        cur.execute('create table tbl2(id2 serial, txt2 text)')
        cur.execute('create table schema1.s1_tbl1(id1 integer, txt1 text)')
        cur.execute('create table tbl3(c3 circle, exclude using gist (c3 with &&))')
        cur.execute('create table "Inh1"(value1 integer) inherits (tbl1)')
        cur.execute('create table inh2(value2 integer) inherits (tbl1, tbl2)')

        # views
        cur.execute('create view vw1 as select * from tbl1')
        cur.execute('''create view schema1.s1_vw1 as
                       select * from schema1.s1_tbl1''')

        # materialized views
        cur.execute('create materialized view mvw1 as select * from tbl1')
        cur.execute('''create materialized view schema1.s1_mvw1 as
                       select * from schema1.s1_tbl1''')

        # datatype
        cur.execute('create type foo AS (a int, b text)')

        # functions
        cur.execute('''create function func1() returns int language sql as
                       $$select 1$$''')
        cur.execute('''create function schema1.s1_func1() returns int language
                       sql as $$select 2$$''')

        # domains
        cur.execute("create domain gender_t char(1)"
                    " check (value in ('F', 'M'))")
        cur.execute("create domain schema1.smallint_t smallint")
        cur.execute("create domain schema1.bigint_t bigint")
        cur.execute("comment on domain schema1.bigint_t is"
                    " 'a really large integer'")


def teardown_db(conn):
    with conn.cursor() as cur:
        cur.execute('''
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            DROP SCHEMA IF EXISTS schema1 CASCADE;
            DROP SCHEMA IF EXISTS schema2 CASCADE''')
