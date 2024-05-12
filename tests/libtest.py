from pathlib import Path
from typing import Callable, Any
import re
import pytest
import psycopg2
from sillyorm.dbms import postgresql
from sillyorm.dbms import SQLite
from sillyorm.environment import Environment
from sillyorm.sql import Cursor, SqlType


def _pg_conn(tmp_path: Path) -> postgresql.PostgreSQLConnection:
    dbname = re.sub("[^a-zA-Z0-9]", "", str(tmp_path))
    connstr = "host=127.0.0.1 user=postgres password=postgres"

    conn = psycopg2.connect(connstr + " dbname=postgres")
    conn.autocommit = True
    cr = conn.cursor()
    cr.execute(f'CREATE DATABASE "{dbname}";')
    conn.close()

    return postgresql.PostgreSQLConnection(connstr + f" dbname={dbname}")


def _sqlite_conn(tmp_path: Path) -> SQLite.SQLiteConnection:
    dbpath = tmp_path / "test.db"
    return SQLite.SQLiteConnection(str(dbpath))


def with_test_env(fn: Callable[[Environment], None]) -> Any:
    def wrapper(tmp_path: Path, db_conn_fn: Callable[[Path], Any]) -> None:
        env = Environment(db_conn_fn(tmp_path).cursor(), do_commit=False)
        try:
            fn(env)
        except Exception as e:  # pragma: no cover
            raise e
        finally:
            env.cr.rollback()

    return pytest.mark.parametrize(
        "db_conn_fn", [(_sqlite_conn), (_pg_conn)], ids=["SQLite", "PostgreSQL"]
    )(wrapper)


def assert_db_columns(cr: Cursor, table: str, columns: list[tuple[str, SqlType]]) -> None:
    info = [(info.name, info.type) for info in cr.get_table_column_info(table)]
    assert len(info) == len(columns)
    for column in columns:
        assert column in info
