import pytest
import datetime
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns


@with_test_env(True)
def test_field_date(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        date = sillyorm.fields.Date()

    def assert_columns():
        assert_db_columns(
            env.cr, "sale_order", [("id", SqlType.integer()), ("date", SqlType.date())]
        )

    def first():
        env.register_model(SaleOrder)
        env.init_tables()
        assert_columns()

        so_1 = env["sale_order"].create({"date": datetime.date(2024, 5, 7)})
        so_2 = env["sale_order"].create({})

        assert so_1.date == datetime.date(2024, 5, 7)
        assert so_2.date is None

        so_2.date = datetime.date(2025, 5, 7)
        assert so_2.date == datetime.date(2025, 5, 7)

        so_1.date = datetime.date(2023, 5, 7)
        assert so_1.date == datetime.date(2023, 5, 7)

        with pytest.raises(SillyORMException) as e_info:
            so_1.date = datetime.datetime(2026, 5, 7)
        assert str(e_info.value) == "Date value must be date"
        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        env.register_model(SaleOrder)
        env.init_tables()
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.date == datetime.date(2023, 5, 7)
        assert so_2.date == datetime.date(2025, 5, 7)
        so_2.date = None
        assert so_2.date is None

    if is_second:
        second()
    else:
        return first()
