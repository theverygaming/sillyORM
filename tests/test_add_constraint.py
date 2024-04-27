import pytest
import sillyORM
from sillyORM.sql import SqlType
from sillyORM.tests.internal import with_test_env, assert_db_columns
from sillyORM.dbms.SQLite import SQLiteCursor
from sillyORM.dbms.postgresql import PostgreSQLCursor


@with_test_env
def test_add_constraint(env):
    class SaleOrder(sillyORM.model.Model):
        _name = "sale_order"

        name = sillyORM.fields.String()

    class SaleOrderLine1(sillyORM.model.Model):
        _name = "sale_order_line"

        product = sillyORM.fields.String()
    
    class SaleOrderLine2(sillyORM.model.Model):
        _name = "sale_order_line"

        product = sillyORM.fields.String()
        sale_order_id = sillyORM.fields.Many2one("sale_order")

    env.register_model(SaleOrder)
    env.register_model(SaleOrderLine1)
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER), ("name", SqlType.VARCHAR)])
    assert_db_columns(env.cr, "sale_order_line", [("id", SqlType.INTEGER), ("product", SqlType.VARCHAR)])

    del env._models["sale_order_line"]  # remove so we can register the SOL model again

    env.register_model(SaleOrderLine2)

    assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER), ("name", SqlType.VARCHAR)])
    assert_db_columns(env.cr, "sale_order_line", [("id", SqlType.INTEGER), ("product", SqlType.VARCHAR), ("sale_order_id", SqlType.INTEGER)])
    
    # test the FOREIGN KEY constraint
    so_1 = env["sale_order"].create({})
    sol_1 = env["sale_order_line"].create({"sale_order_id": so_1.id})

    if isinstance(env.cr, SQLiteCursor):  # SQLite does not support ALTER TABLE ADD CONSTRAINT
        return

    with pytest.raises(Exception) as e_info:
        env["sale_order_line"].create({"sale_order_id": so_1.id + 5})
    if isinstance(env.cr, PostgreSQLCursor):
        assert str(e_info.value) == ('insert or update on table "sale_order_line" violates foreign key constraint "constraint_sale_order_id_FOREIGN_KEY"\n' 
                                     + f'DETAIL:  Key (sale_order_id)=({so_1.id+5}) is not present in table "sale_order".\n')