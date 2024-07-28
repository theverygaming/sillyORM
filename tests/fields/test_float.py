import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns


@with_test_env(True)
def test_field_float(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        price = sillyorm.fields.Float()

    def assert_columns():
        assert_db_columns(
            env.cr, "sale_order", [("id", SqlType.integer()), ("price", SqlType.float())]
        )

    def first():
        env.register_model(SaleOrder)
        assert_columns()

        so_1 = env["sale_order"].create({"price": 123456.789012})
        so_2 = env["sale_order"].create({})

        assert so_1.price == 123456.789012
        assert so_2.price is None

        so_2.price = 340000000000000000000000000000000000000.0
        assert so_2.price == 340000000000000000000000000000000000000.0
        so_2.price = -0.000000000000000000000000000000000000012
        assert so_2.price == -0.000000000000000000000000000000000000012

        so_1.price -= 0.789012
        assert so_1.price == 123456.0

        with pytest.raises(SillyORMException) as e_info:
            so_1.price = "test"
        assert str(e_info.value) == "Float value must be float"
        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        env.register_model(SaleOrder)
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.price == 123456.0
        assert so_2.price == -0.000000000000000000000000000000000000012
        so_2.price = None
        assert so_2.price is None

    if is_second:
        second()
    else:
        return first()
