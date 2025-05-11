import pytest
import psycopg2
import sqlite3
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.dbms.sqlite import SQLiteCursor
from sillyorm.dbms.postgresql import PostgreSQLCursor
from .libtest import with_test_env, assert_db_columns


@with_test_env()
def test_constraints(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        # NOT NULL
        name = sillyorm.fields.String(required=True)
        boringField = sillyorm.fields.String()
        # UNIQUE
        some_identifier_1 = sillyorm.fields.String(unique=True)
        # NOT NULL, UNIQUE
        some_identifier_2 = sillyorm.fields.Text(required=True, unique=True)

    class SaleOrderLine(sillyorm.model.Model):
        _name = "sale_order_line"

        name = sillyorm.fields.String()
        # FOREIGN KEY, UNIQUE
        sale_order_id = sillyorm.fields.Many2one("sale_order", unique=True)

    env.register_model(SaleOrder)
    env.register_model(SaleOrderLine)
    env.init_tables()
    assert_db_columns(
        env.cr,
        "sale_order",
        [
            ("id", SqlType.integer()),
            ("name", SqlType.varchar(255)),
            ("boringField", SqlType.varchar(255)),
            ("some_identifier_1", SqlType.varchar(255)),
            ("some_identifier_2", SqlType.text()),
        ],
    )
    assert_db_columns(
        env.cr,
        "sale_order_line",
        [
            ("id", SqlType.integer()),
            ("name", SqlType.varchar(255)),
            ("sale_order_id", SqlType.integer()),
        ],
    )

    # .. should work
    so_1 = env["sale_order"].create(
        {
            "name": "something",
            "boringField": None,
            "some_identifier_1": "hewwwo",
            "some_identifier_2": "awoo",
        }
    )

    # test NOT NULL on SaleOrder
    env.cr.commit()
    for field_name in ["name", "some_identifier_2"]:
        vals = {
            "name": "name: test",
            "some_identifier_2": "some_identifier_2 test",
            "boringField": None,
        }
        del vals[field_name]
        # sillyORM NOT NULL test
        with pytest.raises(sillyorm.exceptions.SillyORMException) as e_info:
            env["sale_order"].create({**vals, field_name: None})
        assert str(e_info.value) == f"attempted to set required field '{field_name}' to 'None'"
        # Actual DB constraint
        if isinstance(env.cr, PostgreSQLCursor):
            err_type = psycopg2.errors.NotNullViolation
            err_txt = (
                f'null value in column "{field_name}" of relation "sale_order" violates not-null'
                " constraint"
            )
        else:
            err_type = sqlite3.IntegrityError
            err_txt = f"NOT NULL constraint failed: sale_order.{field_name}"
        with pytest.raises(err_type) as e_info:
            env["sale_order"].create(vals)
        assert err_txt in str(e_info.value)
        env.cr.rollback()

    # test UNIQUE on SaleOrder
    env.cr.commit()
    for field_name in ["some_identifier_1", "some_identifier_2"]:

        def _get_vals(n):
            vals = {
                "name": "name: test",
                "some_identifier_2": f"{field_name} test {n}",  # required so always here
                "boringField": "boring value",
            }
            vals[field_name] = f"{field_name} repeated value"
            return vals

        # first one should be oki
        env["sale_order"].create(_get_vals(0))
        # Actual DB constraint
        if isinstance(env.cr, PostgreSQLCursor):
            err_type = psycopg2.errors.UniqueViolation
            err_txt = "duplicate key value violates unique constraint"
        else:
            err_type = sqlite3.IntegrityError
            err_txt = f"UNIQUE constraint failed: sale_order.{field_name}"
        with pytest.raises(err_type) as e_info:
            env["sale_order"].create(_get_vals(1))
        assert err_txt in str(e_info.value)
        env.cr.rollback()

    # test UNIQUE on SaleOrderLine with foreign key
    env.cr.commit()
    vals = {"name": "name: test", "sale_order_id": so_1.id}
    # first one should be oki
    env["sale_order_line"].create(vals)
    env.cr.commit()
    if isinstance(env.cr, PostgreSQLCursor):
        err_type = psycopg2.errors.UniqueViolation
        err_txt = "duplicate key value violates unique constraint"
    else:
        err_type = sqlite3.IntegrityError
        err_txt = f"UNIQUE constraint failed: sale_order_line.sale_order_id"
    with pytest.raises(err_type) as e_info:
        env["sale_order_line"].create(vals)
    assert err_txt in str(e_info.value)
    env.cr.rollback()
