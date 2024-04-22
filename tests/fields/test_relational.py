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
def test_many2one_one2many(tmp_path, db_conn_fn):
    class SaleOrder(sillyORM.model.Model):
        _name = "sale_order"

        name = sillyORM.fields.String()
        line_ids = sillyORM.fields.One2many("sale_order_line", "sale_order_id")

    class SaleOrderLine(sillyORM.model.Model):
        _name = "sale_order_line"

        product = sillyORM.fields.String()
        sale_order_id = sillyORM.fields.Many2one("sale_order")

    def new_env():
        env = sillyORM.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(SaleOrder)
        env.register_model(SaleOrderLine)
        assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER), ("name", SqlType.VARCHAR)])
        assert_db_columns(env.cr, "sale_order_line", [("id", SqlType.INTEGER), ("product", SqlType.VARCHAR), ("sale_order_id", SqlType.INTEGER)])
        return env

    env = new_env()
    so_1_id = env["sale_order"].create({"name": "order 1"}).id
    so_2_id = env["sale_order"].create({"name": "order 2"}).id

    env = new_env()
    o1_l1 = env["sale_order_line"].create({"product": "p1 4 o1", "sale_order_id": so_1_id})
    o1_l2 = env["sale_order_line"].create({"product": "p2 4 o1", "sale_order_id": so_1_id})

    o2_l1 = env["sale_order_line"].create({"product": "p1 4 o2", "sale_order_id": so_2_id})
    o2_l2 = env["sale_order_line"].create({"product": "p2 4 o2", "sale_order_id": so_2_id})
    o2_l3 = env["sale_order_line"].create({"product": "p3 4 o2", "sale_order_id": so_2_id})

    assert isinstance(o1_l1.sale_order_id, SaleOrder)
    assert o1_l1.sale_order_id.id == so_1_id
    assert o1_l2.sale_order_id.id == so_1_id
    assert o2_l1.sale_order_id.id == so_2_id

    abandoned_so_line1 = env["sale_order_line"].create({"product": "p3 4 o2"})
    abandoned_so_line2 = env["sale_order_line"].create({"product": "p3 4 o2"})
    assert abandoned_so_line1.sale_order_id is None
    assert abandoned_so_line2.sale_order_id is None
    assert env["sale_order_line"].browse([abandoned_so_line1.id, abandoned_so_line2.id]).sale_order_id is None
    abandoned_so_line1.sale_order_id = env["sale_order"].browse(so_1_id)
    assert env["sale_order_line"].browse([abandoned_so_line1.id, abandoned_so_line2.id]).sale_order_id.id == so_1_id
    abandoned_so_line2.sale_order_id = env["sale_order"].browse(so_2_id)
    assert len(list(env["sale_order_line"].browse([abandoned_so_line1.id, abandoned_so_line2.id]).sale_order_id)) == 2


    # TODO: One2many
