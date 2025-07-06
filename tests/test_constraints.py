import pytest
import psycopg2
import sqlite3
import sillyorm
import sqlalchemy
from .libtest import with_test_registry, assert_db_columns


@with_test_registry()
def test_constraints(registry):
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

    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderLine)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        registry,
        "sale_order",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ("boringField", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ("some_identifier_1", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ("some_identifier_2", sqlalchemy.sql.sqltypes.TEXT()),
        ],
    )
    assert_db_columns(
        registry,
        "sale_order_line",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ("sale_order_id", sqlalchemy.sql.sqltypes.INTEGER()),
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
    env.connection.commit()
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
        with pytest.raises(sqlalchemy.exc.IntegrityError) as e_info:
            env["sale_order"].create(vals)
        assert f"NOT NULL constraint failed: sale_order.{field_name}" in str(
            e_info.value
        ) or f'(psycopg2.errors.NotNullViolation) null value in column "{field_name}" of relation "sale_order"' in str(
            e_info.value
        )
        env.connection.rollback()

    # test UNIQUE on SaleOrder
    env.connection.commit()
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
        with pytest.raises(sqlalchemy.exc.IntegrityError) as e_info:
            env["sale_order"].create(_get_vals(1))
        assert f"UNIQUE constraint failed: sale_order.{field_name}" in str(
            e_info.value
        ) or f'(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "sale_order_{field_name}_key"' in str(
            e_info.value
        )
        env.connection.rollback()

    # test UNIQUE on SaleOrderLine with foreign key
    env.connection.commit()
    vals = {"name": "name: test", "sale_order_id": so_1.id}
    # first one should be oki
    env["sale_order_line"].create(vals)
    env.connection.commit()
    with pytest.raises(sqlalchemy.exc.IntegrityError) as e_info:
        env["sale_order_line"].create(vals)
    assert f"UNIQUE constraint failed: sale_order_line.sale_order_id" in str(
        e_info.value
    ) or f'(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "sale_order_line_sale_order_id_key"' in str(
        e_info.value
    )
    env.connection.rollback()
