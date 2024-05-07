import pytest
import datetime
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.tests.internal import with_test_env, assert_db_columns
from sillyorm.exceptions import SillyORMException


@with_test_env
def test_field_date(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        date = sillyorm.fields.Date()

    env.register_model(SaleOrder)
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER), ("date", SqlType.DATE)])

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
