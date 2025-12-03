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

        f1 = sillyorm.fields.String(required=True)
        f2 = sillyorm.fields.String()

        @sillyorm.model.constraints("f1")
        def constraint_f1(self):
            for record in self:
                if record.f1 == "1":
                    raise Exception("f1 == '1'")

        @sillyorm.model.constraints("f2")
        def constraint_f2(self):
            for record in self:
                if record.f2 == "2":
                    raise Exception("f2 == '2'")

        @sillyorm.model.constraints("f1", "f2")
        def constraint_f1_f2(self):
            for record in self:
                if record.f1 == record.f2:
                    raise Exception("f1 == f2")

    registry.register_model(SaleOrder)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment(
        autocommit=True
    )  # autocommit because we are testing autocommit transaction handling

    ## Create
    with pytest.raises(Exception) as e_info:
        env["sale_order"].create(
            {
                "f1": "1",
            }
        )
    assert str(e_info.value) == f"f1 == '1'"
    with pytest.raises(Exception) as e_info:
        env["sale_order"].create(
            {
                "f1": "x",
                "f2": "2",
            }
        )
    assert str(e_info.value) == f"f2 == '2'"
    with pytest.raises(Exception) as e_info:
        env["sale_order"].create(
            {
                "f1": "this should never exist",
                "f2": "this should never exist",
            }
        )
    assert str(e_info.value) == f"f1 == f2"
    # data should never be created (transaction aborted)
    assert env["sale_order"].search([("f1", "=", "this should never exist")]).ids == []

    ## Write
    so1 = env["sale_order"].create(
        {
            "f1": "abc",
            "f2": "1",
        }
    )
    so1.write(
        {
            "f1": "f1",
            "f2": "f2",
        }
    )

    with pytest.raises(Exception) as e_info:
        so1.f1 = "1"
    assert str(e_info.value) == f"f1 == '1'"
    # fields shouldn't change (transaction aborted)
    assert so1.f1 == "f1"
    assert so1.f2 == "f2"

    with pytest.raises(Exception) as e_info:
        so1.write(
            {
                "f2": "2",
            }
        )
    assert str(e_info.value) == f"f2 == '2'"
    # fields shouldn't change (transaction aborted)
    assert so1.f1 == "f1"
    assert so1.f2 == "f2"

    with pytest.raises(Exception) as e_info:
        so1.write(
            {
                "f1": "abcdef",
                "f2": "abcdef",
            }
        )
    assert str(e_info.value) == f"f1 == f2"
    # fields shouldn't change (transaction aborted)
    assert so1.f1 == "f1"
    assert so1.f2 == "f2"
