from pathlib import Path
from typing import Callable, Any
import re
import pytest
import psycopg2
import sillyorm
from sillyorm.dbms import postgresql
from sillyorm.dbms import sqlite
from sillyorm.environment import Environment
from sillyorm.sql import Cursor, SqlType, SqlConstraint


def _pg_conn(tmp_path: Path) -> postgresql.PostgreSQLConnection:
    dbname = f"pytestdb{hash(str(tmp_path))}"
    connstr = "host=127.0.0.1 user=postgres password=postgres"

    conn = psycopg2.connect(connstr + " dbname=postgres")
    conn.autocommit = True
    cr = conn.cursor()
    cr.execute(f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{dbname}';")
    if cr.fetchone() is None:
        cr.execute(f'CREATE DATABASE "{dbname}";')
    conn.close()

    return postgresql.PostgreSQLConnection(connstr + f" dbname={dbname}")


def _sqlite_conn(tmp_path: Path) -> sqlite.SQLiteConnection:
    dbpath = tmp_path / "test.db"
    return sqlite.SQLiteConnection(str(dbpath))


def with_test_env(reinit: bool = False) -> Any:
    def inner_fn(
        fn: Callable[[Environment], None] | Callable[[Environment, bool, Any], Any],
    ) -> Any:
        def wrapper(tmp_path: Path, db_conn_fn: Callable[[Path], Any]) -> None:
            def run_test(is_second: bool = False, prev_ret=None) -> Any:
                env = Environment(db_conn_fn(tmp_path).cursor(), do_commit=reinit)
                try:
                    if reinit:
                        return fn(env, is_second, prev_ret)
                    fn(env)
                except Exception as e:  # pragma: no cover
                    raise e
                finally:
                    if not reinit:
                        env.cr.rollback()

            ret = run_test()
            if reinit:
                run_test(True, ret)

        return pytest.mark.parametrize(
            "db_conn_fn", [(_sqlite_conn), (_pg_conn)], ids=["SQLite", "PostgreSQL"]
        )(wrapper)

    return inner_fn


def assert_db_columns(cr: Cursor, table: str, columns: list[tuple[str, SqlType]]) -> None:
    info = [(info.name, info.type) for info in cr.get_table_column_info(table)]
    assert len(info) == len(columns)
    for column in columns:
        assert column in info

def assert_db_columns_with_constraints(cr: Cursor, table: str, columns: list[tuple[str, SqlType, [SqlConstraint]]]) -> None:
    info = [(info.name, info.type, sorted(info.constraints)) for info in cr.get_table_column_info(table)]
    assert len(info) == len(columns)
    for column in columns:
        # TODO: fix this
        assert column in info


def generic_field_test(
    fieldClass: sillyorm.fields.Field,
    fieldClassArgs: list[tuple[list[Any], dict[str, Any]]],
    sql_types: list[SqlType],
    valid_write_vals: list[Any],
    invalid_write_vals: list[Any],
    env: Environment,
    is_second: bool,
    prev_return: Any,
) -> Any:
    # some sanity checks on the input
    assert len(fieldClassArgs) == len(valid_write_vals)

    class Model(sillyorm.model.Model):
        _name = "model"

    for i, fca in enumerate(fieldClassArgs):
        attr = setattr(Model, f"field_n_{i}", fieldClass(*fca[0], **fca[1]))
        Model.__dict__[f"field_n_{i}"].__set_name__(Model, f"field_n_{i}")

    def assert_columns():
        columns = []
        for i in range(len(valid_write_vals)):
            columns.append((f"field_n_{i}", sql_types[i]))
        assert_db_columns(env.cr, "model", [("id", SqlType.integer())] + columns)

    def get_expected_vals(offset: int):
        vals = {
            f"field_n_{(fi+offset) % len(valid_write_vals)}": v
            for fi, v in enumerate(valid_write_vals)
        }
        return vals

    def first():
        env.register_model(Model)
        env.init_tables()
        assert_columns()

        # create test
        records = []
        for i in range(len(valid_write_vals)):
            records.append(env["model"].create(get_expected_vals(i)))

        for i, record in enumerate(records):
            vals = get_expected_vals(i)
            for k, v in vals.items():
                assert getattr(record, k) == v

        # invalid values test
        for i, val in enumerate(invalid_write_vals):
            with pytest.raises(sillyorm.exceptions.SillyORMException) as e_info:
                setattr(records[i % len(records)], f"field_n_{i % len(valid_write_vals)}", val)

        for i, record in enumerate(records):
            vals = get_expected_vals(i)
            for k, v in vals.items():
                assert getattr(record, k) == v

        # change test
        for i, record in enumerate(records):
            vals = get_expected_vals(i + 1)
            for k, v in vals.items():
                setattr(record, k, v)

        for i, record in enumerate(records):
            vals = get_expected_vals(i + 1)
            for k, v in vals.items():
                assert getattr(record, k) == v

        return [r.id for r in records]

    def second():
        assert_columns()
        env.register_model(Model)
        env.init_tables()
        assert_columns()
        for i, record_id in enumerate(prev_return):
            record = env["model"].browse(record_id)
            vals = get_expected_vals(i + 1)
            for k, v in vals.items():
                assert getattr(record, k) == v

    if is_second:
        second()
    else:
        return first()
