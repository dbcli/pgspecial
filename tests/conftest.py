import pytest
from dbutils import create_db, db_connection, setup_db, teardown_db, TEST_DB_NAME
from pgspecial.main import PGSpecial


@pytest.yield_fixture(scope="module")
def connection():
    create_db(TEST_DB_NAME)
    connection = db_connection(TEST_DB_NAME)
    setup_db(connection)
    yield connection

    teardown_db(connection)
    connection.close()


@pytest.fixture
def cursor(connection):
    with connection.cursor() as cur:
        return cur


@pytest.fixture
def executor(connection):
    cur = connection.cursor()
    pgspecial = PGSpecial()

    def query_runner(sql):
        results = []
        for title, rows, headers, status in pgspecial.execute(cur=cur, sql=sql):
            if rows:
                results.extend((title, list(rows), headers, status))
            else:
                results.extend((title, None, headers, status))
        return results

    return query_runner
