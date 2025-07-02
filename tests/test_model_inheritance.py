import pytest
import sillyorm
import sqlalchemy
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_registry, assert_db_columns


@with_test_registry()
def test_inheritance_copy(registry):
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
            registry,
            "sale_order",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )
        assert_db_columns(
            registry,
            "sale_order_copy",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )
        assert_db_columns(
            registry,
            "sale_order_extra_field",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
                ("extrafield", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )
        assert_db_columns(
            registry,
            "sale_order_extra_extra_field",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
                ("extrafield", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
                ("extrafield2", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )
        assert_db_columns(
            registry,
            "sale_order_extra_field_override",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.DATE()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=123)),
                ("extrafield", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )

    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderCopy)
    registry.register_model(SaleOrderExtraField)
    registry.register_model(SaleOrderExtraExtraField)
    registry.register_model(SaleOrderExtraFieldOverride)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
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


@with_test_registry()
def test_inheritance_abstract(registry):
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
            registry,
            "sale_order",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )
        assert_db_columns(
            registry,
            "sale_order_extra_field",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
                ("extrafield", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )

    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderExtraField)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
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


@with_test_registry()
def test_inheritance_abstract_via_registry(registry):
    class SaleOrderAbstract(sillyorm.model.AbstractModel):
        _name = "sale_order_abstract"
        line_count = sillyorm.fields.Integer()
        teststr = sillyorm.fields.String()

        def testfn(self):
            return f"SaleOrderAbstract"

    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"
        _inherits = ["sale_order_abstract"]

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
            registry,
            "sale_order",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )
        assert_db_columns(
            registry,
            "sale_order_extra_field",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("line_count", sqlalchemy.sql.sqltypes.INTEGER()),
                ("teststr", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
                ("extrafield", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )

    registry.register_model(SaleOrderAbstract)
    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderExtraField)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert not sqlalchemy.inspect(registry.engine).has_table("sale_order_abstract")
    assert env["sale_order_abstract"]._table is None
    assert not env["sale_order_abstract"]._has_table
    assert env["sale_order"]._has_table
    assert env["sale_order"]._table is not None
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
