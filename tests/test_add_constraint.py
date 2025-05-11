import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.dbms.sqlite import SQLiteCursor
from sillyorm.dbms.postgresql import PostgreSQLCursor
from .libtest import with_test_env, assert_db_columns


@with_test_env()
def test_add_constraint(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()

    class SaleOrderLine1(sillyorm.model.Model):
        _name = "sale_order_line"

        product = sillyorm.fields.String()

    class SaleOrderLine2(sillyorm.model.Model):
        _name = "sale_order_line"

        product = sillyorm.fields.String()
        sale_order_id = sillyorm.fields.Many2one("sale_order")

    env.register_model(SaleOrder)
    env.register_model(SaleOrderLine1)
    env.init_tables()
    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(255))]
    )
    assert_db_columns(
        env.cr, "sale_order_line", [("id", SqlType.integer()), ("product", SqlType.varchar(255))]
    )

    del env._models["sale_order_line"]  # remove so we can register the SOL model again
    del env._lmodels["sale_order_line"]  # remove so we can register the SOL model again

    env.register_model(SaleOrderLine2)
    env.init_tables()

    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(255))]
    )
    assert_db_columns(
        env.cr,
        "sale_order_line",
        [
            ("id", SqlType.integer()),
            ("product", SqlType.varchar(255)),
            ("sale_order_id", SqlType.integer()),
        ],
    )

    # test the FOREIGN KEY constraint
    so_1 = env["sale_order"].create({})
    sol_1 = env["sale_order_line"].create({"sale_order_id": so_1.id})

    if isinstance(env.cr, SQLiteCursor):  # SQLite does not support ALTER TABLE ADD CONSTRAINT
        return

    with pytest.raises(Exception) as e_info:
        env["sale_order_line"].create({"sale_order_id": so_1.id + 5})
    if isinstance(env.cr, PostgreSQLCursor):
        assert str(e_info.value) == (
            'insert or update on table "sale_order_line" violates foreign key constraint'
            ' "constraint_sale_order_id_FOREIGNKEY"\n'
            + f'DETAIL:  Key (sale_order_id)=({so_1.id+5}) is not present in table "sale_order".\n'
        )
