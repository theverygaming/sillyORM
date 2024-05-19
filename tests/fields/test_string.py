import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns


@with_test_env(True)
def test_field_string(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()

    def assert_columns():
        assert_db_columns(
            env.cr, "sale_order", [("id", SqlType.INTEGER()), ("name", SqlType.VARCHAR(255))]
        )

    def first():
        env.register_model(SaleOrder)
        assert_columns()

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

        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        env.register_model(SaleOrder)
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.name == "hello world"
        assert so_2.name == "test"

    if is_second:
        second()
    else:
        return first()
