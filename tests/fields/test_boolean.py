import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns


@with_test_env(True)
def test_field_boolean(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        is_confirmed = sillyorm.fields.Boolean()

    def assert_columns():
        assert_db_columns(
            env.cr, "sale_order", [("id", SqlType.integer()), ("is_confirmed", SqlType.boolean())]
        )

    def first():
        env.register_model(SaleOrder)
        assert_columns()

        so_1 = env["sale_order"].create({"is_confirmed": True})
        so_2 = env["sale_order"].create({})

        assert so_1.is_confirmed is True
        assert so_2.is_confirmed is None

        so_1.is_confirmed = False
        assert so_1.is_confirmed is False

        so_2.is_confirmed = True
        assert so_2.is_confirmed is True

        with pytest.raises(SillyORMException) as e_info:
            so_1.is_confirmed = "test"
        assert str(e_info.value) == "Boolean value must be bool"
        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        env.register_model(SaleOrder)
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.is_confirmed is False
        assert so_2.is_confirmed is True

    if is_second:
        second()
    else:
        return first()
