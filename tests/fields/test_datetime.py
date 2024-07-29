import pytest
import datetime
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns


@with_test_env(True)
def test_field_datetime(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        time = sillyorm.fields.Datetime()

    def assert_columns():
        assert_db_columns(
            env.cr, "sale_order", [("id", SqlType.integer()), ("time", SqlType.timestamp())]
        )

    def first():
        env.register_model(SaleOrder)
        env.init_tables()
        assert_columns()

        so_1 = env["sale_order"].create({"time": datetime.datetime(2024, 5, 7, 12, 59, 30)})
        so_2 = env["sale_order"].create({})

        assert so_1.time == datetime.datetime(2024, 5, 7, 12, 59, 30)
        assert so_2.time is None

        so_2.time = datetime.datetime(2025, 5, 7, 5, 23, 0)
        assert so_2.time == datetime.datetime(2025, 5, 7, 5, 23, 0)

        so_1.time = datetime.datetime(2023, 5, 7, 23, 59, 59)
        assert so_1.time == datetime.datetime(2023, 5, 7, 23, 59, 59)

        assert so_1.time.tzinfo is None

        with pytest.raises(SillyORMException) as e_info:
            so_1.time = datetime.date(2026, 5, 7)
        assert str(e_info.value) == "Datetime value must be datetime"
        with pytest.raises(SillyORMException) as e_info:
            so_1.time = datetime.datetime(2026, 5, 7, tzinfo=datetime.UTC)
        assert str(e_info.value) == "Datetime value must be naive"
        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        env.register_model(SaleOrder)
        env.init_tables()
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.time == datetime.datetime(2023, 5, 7, 23, 59, 59)
        assert so_2.time == datetime.datetime(2025, 5, 7, 5, 23, 0)
        so_2.time = None
        assert so_2.time is None

    if is_second:
        second()
    else:
        return first()
