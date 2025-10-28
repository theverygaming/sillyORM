import datetime
import sillyorm
import sqlalchemy
from ..libtest import with_test_registry, generic_field_test


@with_test_registry(True)
def test_field_date(registry, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Date,
        [([], {})] * 4,
        [sqlalchemy.sql.sqltypes.DATE()] * 4,
        [None, datetime.date(2024, 5, 7), datetime.date(2025, 5, 7), datetime.date(2023, 5, 7)],
        ["Test", [], {}, 1.5, datetime.datetime(2026, 5, 7)],
        registry,
        is_second,
        prev_return,
    )


@with_test_registry(False)
def test_field_date_search(registry):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        date = sillyorm.fields.Date()

    registry.register_model(SaleOrder)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()

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
