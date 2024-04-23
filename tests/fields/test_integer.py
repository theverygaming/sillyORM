import re
import pytest
import psycopg2
import sillyORM
from sillyORM import SQLite, postgresql
from sillyORM.sql import SqlType, SqlConstraint

def pg_conn(tmp_path):
    dbname = re.sub('[^a-zA-Z0-9]', '', str(tmp_path))
    connstr = "host=127.0.0.1 user=postgres password=postgres"
    conn = psycopg2.connect(connstr + " dbname=postgres")
    conn.autocommit = True
    cr = conn.cursor()
    cr.execute(f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{dbname}';")
    if cr.fetchone() is None:
        cr.execute(f"CREATE DATABASE {dbname};")

    return postgresql.PostgreSQLConnection(connstr + f" dbname={dbname}")


def sqlite_conn(tmp_path):
    dbpath = tmp_path / "test.db"
    return SQLite.SQLiteConnection(dbpath)


def assert_db_columns(cr, table, columns):
    info = [(info.name, info.type) for info in cr.get_table_column_info(table)]
    assert len(info) == len(columns)
    for column in columns:
        assert column in info


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_field_id(tmp_path, db_conn_fn):
    class SaleOrder(sillyORM.model.Model):
        _name = "sale_order"

        line_count = sillyORM.fields.Integer()

    env = sillyORM.Environment(db_conn_fn(tmp_path).cursor())
    env.register_model(SaleOrder)
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER), ("line_count", SqlType.INTEGER)])

    so_1 = env["sale_order"].create({"line_count": 5})
    so_2 = env["sale_order"].create({})

    assert so_1.line_count == 5
    assert so_2.line_count is None

    so_2.line_count = -32768
    assert so_2.line_count == -32768

    so_1.line_count -= -1
    assert so_1.line_count == 6

    with pytest.raises(Exception) as e_info:
        so_1.line_count = "test"
    assert str(e_info.value) == "Integer value must be int"
