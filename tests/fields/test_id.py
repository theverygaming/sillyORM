import pytest
import sillyORM
from sillyORM.sql import SqlType
from sillyORM.tests.internal import with_test_env, assert_db_columns
from sillyORM.exceptions import SillyORMException


@with_test_env
def test_field_id(env):
    class SaleOrder(sillyORM.model.Model):
        _name = "sale_order"

    env.register_model(SaleOrder)
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER)])

    so_1 = env["sale_order"].create({})
    so_2 = env["sale_order"].create({})

    assert so_1.id == 1
    assert so_2.id == 2

    with pytest.raises(SillyORMException) as e_info:
        so_1.id = 5
    assert str(e_info.value) == "cannot set id"
