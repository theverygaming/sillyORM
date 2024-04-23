import re
import pytest
import psycopg2
from . import postgresql, SQLite
from .environment import Environment


def _pg_conn(tmp_path):
    dbname = re.sub('[^a-zA-Z0-9]', '', str(tmp_path))
    connstr = "host=127.0.0.1 user=postgres password=postgres"
    with psycopg2.connect(connstr + " dbname=postgres") as conn:
        conn.autocommit = True
        cr = conn.cursor()
        print(dbname)
        cr.execute(f"CREATE DATABASE {dbname};")

    return postgresql.PostgreSQLConnection(connstr + f" dbname={dbname}")

def _sqlite_conn(tmp_path):
    dbpath = tmp_path / "test.db"
    return SQLite.SQLiteConnection(dbpath)


def with_test_env(fn):
    def wrapper(tmp_path, db_conn_fn):
        env = Environment(db_conn_fn(tmp_path).cursor())
        fn(env)
    return pytest.mark.parametrize("db_conn_fn", [(_sqlite_conn), (_pg_conn)], ids=["SQLite", "PostgreSQL"])(wrapper)
