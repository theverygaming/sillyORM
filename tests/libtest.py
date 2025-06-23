from pathlib import Path
from typing import Callable, Any
import re
import pytest
import psycopg2
import sillyorm
import sqlalchemy


def _pg_conn(tmp_path: Path) -> str:
    dbname = f"pytestdb{hash(str(tmp_path))}"
    connstr = "host=127.0.0.1 user=postgres password=postgres"

    conn = psycopg2.connect(connstr + " dbname=postgres")
    conn.autocommit = True
    cr = conn.cursor()
    cr.execute(f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{dbname}';")
    if cr.fetchone() is None:
        cr.execute(f'CREATE DATABASE "{dbname}";')
    conn.close()

    return f"postgresql+psycopg2://postgres:postgres@127.0.0.1/{dbname}"


def _sqlite_conn(tmp_path: Path) -> str:
    dbpath = tmp_path / "test.db"
    return f"sqlite:///{dbpath}"


def with_test_registry(reinit: bool = False, with_request: bool = False) -> Any:
    def inner_fn(
        fn: Callable[[sillyorm.Registry], None] | Callable[[sillyorm.Registry, bool, Any], Any],
    ) -> Any:
        def wrapper(tmp_path: Path, db_conn_fn: Callable[[Path], Any], request) -> None:
            def run_test(is_second: bool = False, prev_ret=None) -> Any:
                registry = sillyorm.Registry(db_conn_fn(tmp_path))
                try:
                    args = []
                    if with_request:
                        args.append(request)
                    args.append(registry)
                    if reinit:
                        args += [is_second, prev_ret]
                    return fn(*args)
                except Exception as e:  # pragma: no cover
                    raise e

            ret = run_test()
            if reinit:
                run_test(True, ret)

        return pytest.mark.parametrize(
            "db_conn_fn", [(_sqlite_conn), (_pg_conn)], ids=["SQLite", "PostgreSQL"]
        )(wrapper)

    return inner_fn


def assert_db_columns(registry, table_name: str, expected_columns: list[tuple[str, type]]) -> None:
    def sqlalchemy_type_comparable(t):
        return [
            repr(type(t)),
            repr({k: v for k, v in t.__dict__.items() if not k.startswith("_")}),
        ]

    inspector = sqlalchemy.inspect(registry.engine)
    columns_info = inspector.get_columns(table_name)

    actual = [(col["name"], sqlalchemy_type_comparable(col["type"])) for col in columns_info]
    expected = [(name, sqlalchemy_type_comparable(col_type)) for name, col_type in expected_columns]

    assert len(actual) == len(
        expected
    ), f"Expected {len(expected)} columns, got {len(actual)}: {actual}"

    for col in expected:
        assert col in actual, f"Missing or mismatched column: {col}, found: {actual}"


def generic_field_test(
    fieldClass: sillyorm.fields.Field,
    fieldClassArgs: list[tuple[list[Any], dict[str, Any]]],
    sql_types: list[sqlalchemy.types.TypeEngine],
    valid_write_vals: list[Any],
    invalid_write_vals: list[Any],
    registry: sillyorm.Registry,
    is_second: bool,
    prev_return: Any,
) -> Any:
    # some sanity checks on the input
    assert len(fieldClassArgs) == len(valid_write_vals)

    class Model(sillyorm.model.Model):
        _name = "model"

    for i, fca in enumerate(fieldClassArgs):
        setattr(Model, f"field_n_{i}", fieldClass(*fca[0], **fca[1]))
        Model.__dict__[f"field_n_{i}"].__set_name__(Model, f"field_n_{i}")

    def assert_columns():
        columns = [("id", sqlalchemy.sql.sqltypes.INTEGER())]
        for i in range(len(valid_write_vals)):
            columns.append((f"field_n_{i}", sql_types[i]))
        assert_db_columns(registry, "model", columns)

    def get_expected_vals(offset: int):
        vals = {
            f"field_n_{(fi+offset) % len(valid_write_vals)}": v
            for fi, v in enumerate(valid_write_vals)
        }
        return vals

    def first():
        registry.register_model(Model)
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment(autocommit=True)
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
            with pytest.raises(sillyorm.exceptions.SillyORMException):
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
        registry.register_model(Model)
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment(autocommit=True)
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
