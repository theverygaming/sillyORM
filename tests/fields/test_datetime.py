import pytest
import datetime
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns

TZ_EST = datetime.timezone(datetime.timedelta(hours=-5))


@with_test_env(True)
def test_field_datetime(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        time = sillyorm.fields.Datetime(None)
        time_est = sillyorm.fields.Datetime(TZ_EST)

    def assert_columns():
        assert_db_columns(
            env.cr,
            "sale_order",
            [
                ("id", SqlType.integer()),
                ("time", SqlType.timestamp()),
                ("time_est", SqlType.timestamp()),
            ],
        )

    def first():
        env.register_model(SaleOrder)
        env.init_tables()
        assert_columns()

        so_1 = env["sale_order"].create(
            {
                "time": datetime.datetime(2024, 5, 7, 12, 59, 30),
                "time_est": datetime.datetime(2024, 5, 7, 12, 59, 30, tzinfo=TZ_EST),
            }
        )
        so_2 = env["sale_order"].create({})

        assert so_1.time == datetime.datetime(2024, 5, 7, 12, 59, 30)
        assert so_2.time is None
        assert so_1.time_est == datetime.datetime(2024, 5, 7, 12, 59, 30, tzinfo=TZ_EST)
        assert so_2.time_est is None

        so_2.time = datetime.datetime(2025, 5, 7, 5, 23, 0)
        assert so_2.time == datetime.datetime(2025, 5, 7, 5, 23, 0)
        so_2.time_est = datetime.datetime(2025, 5, 7, 5, 23, 0, tzinfo=TZ_EST)
        assert so_2.time_est == datetime.datetime(2025, 5, 7, 5, 23, 0, tzinfo=TZ_EST)

        so_1.time = datetime.datetime(2023, 5, 7, 23, 59, 59)
        assert so_1.time == datetime.datetime(2023, 5, 7, 23, 59, 59)
        so_1.time_est = datetime.datetime(2023, 5, 7, 23, 59, 59, tzinfo=TZ_EST)
        assert so_1.time_est == datetime.datetime(2023, 5, 7, 23, 59, 59, tzinfo=TZ_EST)

        assert so_1.time.tzinfo is None
        assert so_1.time_est.tzinfo == TZ_EST

        with pytest.raises(SillyORMException) as e_info:
            so_1.time = datetime.date(2026, 5, 7)
        assert str(e_info.value) == "Datetime value must be datetime"
        with pytest.raises(SillyORMException) as e_info:
            so_1.time = datetime.datetime(2026, 5, 7, tzinfo=datetime.UTC)
        assert str(e_info.value) == "Datetime field expected tzinfo 'None' and got 'UTC'"
        with pytest.raises(SillyORMException) as e_info:
            so_1.time_est = datetime.datetime(2026, 5, 7, tzinfo=datetime.UTC)
        assert str(e_info.value) == "Datetime field expected tzinfo 'UTC-05:00' and got 'UTC'"
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
        assert so_1.time_est == datetime.datetime(2023, 5, 7, 23, 59, 59, tzinfo=TZ_EST)
        assert so_2.time_est == datetime.datetime(2025, 5, 7, 5, 23, 0, tzinfo=TZ_EST)
        so_2.time = None
        assert so_2.time is None
        so_2.time_est = None
        assert so_2.time_est is None

    if is_second:
        second()
    else:
        return first()


@with_test_env(False)
def test_field_datetime_search(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        time = sillyorm.fields.Datetime(None)

    env.register_model(SaleOrder)
    env.init_tables()

    so_1 = env["sale_order"].create({"time": datetime.datetime(2025, 1, 30, 20, 24, 28)})
    so_2 = env["sale_order"].create({"time": datetime.datetime(2025, 1, 30, 20, 24, 29)})
    so_3 = env["sale_order"].create({"time": datetime.datetime(2025, 1, 30, 20, 24, 30)})
    so_4 = env["sale_order"].create({"time": datetime.datetime(2024, 1, 10, 11, 12, 13)})
    so_5 = env["sale_order"].create({"time": datetime.datetime(2020, 1, 1, 1, 1, 1)})
    so_6 = env["sale_order"].create({})

    # Time range
    assert env["sale_order"].search(
        [
            ("time", ">=", datetime.datetime(2024, 1, 10, 11, 12, 13)),
            "&",
            ("time", "<", datetime.datetime(2025, 1, 30, 20, 24, 29)),
        ]
    )._ids == [1, 4]

    # Equals
    assert env["sale_order"].search(
        [("time", "=", datetime.datetime(2025, 1, 30, 20, 24, 28))]
    )._ids == [1]
    assert env["sale_order"].search(
        [("time", "=", datetime.datetime(2025, 1, 30, 20, 24, 29))]
    )._ids == [2]
    assert env["sale_order"].search(
        [("time", "=", datetime.datetime(2024, 1, 10, 11, 12, 13))]
    )._ids == [4]
    assert env["sale_order"].search([("time", "=", None)])._ids == [6]

    # Not equals
    assert env["sale_order"].search(
        [("time", "!=", datetime.datetime(2025, 1, 30, 20, 24, 29))]
    )._ids == [1, 3, 4, 5]
    assert env["sale_order"].search(
        [("time", "!=", datetime.datetime(2024, 1, 10, 11, 12, 13))]
    )._ids == [1, 2, 3, 5]
    assert env["sale_order"].search([("time", "!=", None)])._ids == [1, 2, 3, 4, 5]

    # Greater than
    assert env["sale_order"].search(
        [("time", ">", datetime.datetime(2025, 1, 30, 20, 24, 28))]
    )._ids == [2, 3]

    # Less than
    assert env["sale_order"].search(
        [("time", "<", datetime.datetime(2025, 1, 30, 20, 24, 29))]
    )._ids == [1, 4, 5]

    # Greater than or equal
    assert env["sale_order"].search(
        [("time", ">=", datetime.datetime(2025, 1, 30, 20, 24, 28))]
    )._ids == [1, 2, 3]

    # Less than or equal
    assert env["sale_order"].search(
        [("time", "<=", datetime.datetime(2025, 1, 30, 20, 24, 29))]
    )._ids == [1, 2, 4, 5]
