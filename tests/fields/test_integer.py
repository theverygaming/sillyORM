import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.tests.internal import with_test_env, assert_db_columns
from sillyorm.exceptions import SillyORMException


@with_test_env
def test_field_id(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        line_count = sillyorm.fields.Integer()

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

    with pytest.raises(SillyORMException) as e_info:
        so_1.line_count = "test"
    assert str(e_info.value) == "Integer value must be int"
