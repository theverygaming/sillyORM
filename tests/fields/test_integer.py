import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns


@with_test_env(True)
def test_field_id(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        line_count = sillyorm.fields.Integer()

    def assert_columns():
        assert_db_columns(
            env.cr, "sale_order", [("id", SqlType.integer()), ("line_count", SqlType.integer())]
        )

    def first():
        env.register_model(SaleOrder)
        assert_columns()

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
        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        env.register_model(SaleOrder)
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.line_count == 6
        assert so_2.line_count == -32768

    if is_second:
        second()
    else:
        return first()
