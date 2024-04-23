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


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_field_id(tmp_path, db_conn_fn):
    with pytest.raises(Exception) as e_info:
        class SaleOrder(sillyORM.model.Model):
            _name = "sale_order"
            impossible = sillyORM.fields.Field()
    assert str(e_info.value) == "_sql_type must be set"
