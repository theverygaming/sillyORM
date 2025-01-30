import datetime
import sillyorm
from ..libtest import with_test_env, generic_field_test


@with_test_env(True)
def test_field_date(env, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Date,
        [([], {})] * 4,
        [sillyorm.sql.SqlType.date()] * 4,
        [None, datetime.date(2024, 5, 7), datetime.date(2025, 5, 7), datetime.date(2023, 5, 7)],
        ["Test", [], {}, 1.5, datetime.datetime(2026, 5, 7)],
        env,
        is_second,
        prev_return,
    )


@with_test_env(False)
def test_field_date_search(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        date = sillyorm.fields.Date()

    env.register_model(SaleOrder)
    env.init_tables()

    so_1 = env["sale_order"].create({"date": datetime.date(2025, 1, 25)})
    so_2 = env["sale_order"].create({"date": datetime.date(2025, 1, 26)})
    so_3 = env["sale_order"].create({"date": datetime.date(2025, 1, 27)})
    so_4 = env["sale_order"].create({"date": datetime.date(2024, 1, 10)})
    so_5 = env["sale_order"].create({"date": datetime.date(2020, 1, 1)})
    so_6 = env["sale_order"].create({})

    # Time range
    assert env["sale_order"].search(
        [
            ("date", ">=", datetime.date(2024, 1, 10)),
            "&",
            ("date", "<", datetime.date(2025, 1, 26)),
        ]
    )._ids == [1, 4]

    # Equals
    assert env["sale_order"].search([("date", "=", datetime.date(2025, 1, 25))])._ids == [1]
    assert env["sale_order"].search([("date", "=", datetime.date(2025, 1, 26))])._ids == [2]
    assert env["sale_order"].search([("date", "=", datetime.date(2024, 1, 10))])._ids == [4]
    assert env["sale_order"].search([("date", "=", None)])._ids == [6]

    # Not equals
    assert env["sale_order"].search([("date", "!=", datetime.date(2025, 1, 26))])._ids == [
        1,
        3,
        4,
        5,
    ]
    assert env["sale_order"].search([("date", "!=", datetime.date(2024, 1, 10))])._ids == [
        1,
        2,
        3,
        5,
    ]
    assert env["sale_order"].search([("date", "!=", None)])._ids == [1, 2, 3, 4, 5]

    # Greater than
    assert env["sale_order"].search([("date", ">", datetime.date(2025, 1, 25))])._ids == [2, 3]

    # Less than
    assert env["sale_order"].search([("date", "<", datetime.date(2025, 1, 26))])._ids == [1, 4, 5]

    # Greater than or equal
    assert env["sale_order"].search([("date", ">=", datetime.date(2025, 1, 25))])._ids == [1, 2, 3]

    # Less than or equal
    assert env["sale_order"].search([("date", "<=", datetime.date(2025, 1, 26))])._ids == [
        1,
        2,
        4,
        5,
    ]
