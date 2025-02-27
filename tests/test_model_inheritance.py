import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_env, assert_db_columns


@with_test_env()
def test_inheritance_copy(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        line_count = sillyorm.fields.Integer()
        teststr = sillyorm.fields.String()

    class SaleOrderCopy(SaleOrder):
        _name = "sale_order_copy"

    class SaleOrderExtraField(SaleOrder):
        _name = "sale_order_extra_field"

        extrafield = sillyorm.fields.String()

    class SaleOrderExtraExtraField(SaleOrderExtraField):
        _name = "sale_order_extra_extra_field"

        extrafield2 = sillyorm.fields.String()

    class SaleOrderExtraFieldOverride(SaleOrderExtraField):
        _name = "sale_order_extra_field_override"

        teststr = sillyorm.fields.String(length=123)
        line_count = sillyorm.fields.Date()

    def assert_columns():
        assert_db_columns(
            env.cr,
            "sale_order",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("teststr", SqlType.varchar(255)),
            ],
        )
        assert_db_columns(
            env.cr,
            "sale_order_copy",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("teststr", SqlType.varchar(255)),
            ],
        )
        assert_db_columns(
            env.cr,
            "sale_order_extra_field",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("teststr", SqlType.varchar(255)),
                ("extrafield", SqlType.varchar(255)),
            ],
        )
        assert_db_columns(
            env.cr,
            "sale_order_extra_extra_field",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("teststr", SqlType.varchar(255)),
                ("extrafield", SqlType.varchar(255)),
                ("extrafield2", SqlType.varchar(255)),
            ],
        )
        assert_db_columns(
            env.cr,
            "sale_order_extra_field_override",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.date()),
                ("teststr", SqlType.varchar(123)),
                ("extrafield", SqlType.varchar(255)),
            ],
        )

    env.register_model(SaleOrder)
    env.register_model(SaleOrderCopy)
    env.register_model(SaleOrderExtraField)
    env.register_model(SaleOrderExtraExtraField)
    env.register_model(SaleOrderExtraFieldOverride)
    env.init_tables()
    assert_columns()

    assert len(env["sale_order"].search([])) == 0
    assert len(env["sale_order_copy"].search([])) == 0
    assert len(env["sale_order_extra_field"].search([])) == 0
    assert len(env["sale_order_extra_extra_field"].search([])) == 0
    assert len(env["sale_order_extra_field_override"].search([])) == 0

    env["sale_order"].create({"line_count": 5})
    env["sale_order"].create({})

    assert env["sale_order"].search([])._ids == [1, 2]
    assert len(env["sale_order_copy"].search([])) == 0
    assert len(env["sale_order_extra_field"].search([])) == 0
    assert len(env["sale_order_extra_extra_field"].search([])) == 0
    assert len(env["sale_order_extra_field_override"].search([])) == 0

    env["sale_order_extra_field"].create({"line_count": 5, "extrafield": "test extra field"})

    assert env["sale_order"].search([])._ids == [1, 2]
    assert len(env["sale_order_copy"].search([])) == 0
    assert env["sale_order_extra_field"].search([])._ids == [1]
    assert len(env["sale_order_extra_extra_field"].search([])) == 0
    assert len(env["sale_order_extra_field_override"].search([])) == 0


@with_test_env()
def test_inheritance_abstract(env):
    class SaleOrderAbstract(sillyorm.model.Model):
        line_count = sillyorm.fields.Integer()
        teststr = sillyorm.fields.String()

        def testfn(self):
            return f"SaleOrderAbstract"

    class SaleOrder(SaleOrderAbstract):
        _name = "sale_order"

        def testfn(self):
            ret = super().testfn()
            return f"{ret} SaleOrder"

    class SaleOrderExtraField(SaleOrder):
        _name = "sale_order_extra_field"

        extrafield = sillyorm.fields.String()

        def testfn(self):
            ret = super().testfn()
            return f"{ret} SaleOrderExtraField"

    def assert_columns():
        assert_db_columns(
            env.cr,
            "sale_order",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("teststr", SqlType.varchar(255)),
            ],
        )
        assert_db_columns(
            env.cr,
            "sale_order_extra_field",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("teststr", SqlType.varchar(255)),
                ("extrafield", SqlType.varchar(255)),
            ],
        )

    env.register_model(SaleOrder)
    env.register_model(SaleOrderExtraField)
    env.init_tables()
    assert_columns()

    assert len(env["sale_order"].search([])) == 0
    assert len(env["sale_order_extra_field"].search([])) == 0

    env["sale_order"].create({"line_count": 5})
    env["sale_order"].create({})

    assert env["sale_order"].search([])._ids == [1, 2]
    assert len(env["sale_order_extra_field"].search([])) == 0

    env["sale_order_extra_field"].create({"line_count": 5, "extrafield": "test extra field"})

    assert env["sale_order"].search([])._ids == [1, 2]
    assert env["sale_order_extra_field"].search([])._ids == [1]

    assert env["sale_order"].testfn() == "SaleOrderAbstract SaleOrder"
    assert (
        env["sale_order_extra_field"].testfn() == "SaleOrderAbstract SaleOrder SaleOrderExtraField"
    )
