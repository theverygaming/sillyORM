import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.tests.internal import with_test_env, assert_db_columns
from sillyorm.exceptions import SillyORMException


@with_test_env
def test_field_string(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()

    env.register_model(SaleOrder)
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER), ("name", SqlType.VARCHAR_255)])

    so_1 = env["sale_order"].create({"name": "order 1"})
    so_2 = env["sale_order"].create({})
    
    assert so_1.name == "order 1"
    assert so_2.name is None

    so_2.name = "test"
    assert so_2.name == "test"

    so_1.name = "hello world"
    assert so_1.name == "hello world"
    
    with pytest.raises(SillyORMException) as e_info:
        so_1.name = 5
    assert str(e_info.value) == "String value must be str"
