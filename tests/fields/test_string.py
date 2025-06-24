import pytest
import sillyorm
import sqlalchemy
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_registry, assert_db_columns


@with_test_registry(True)
def test_field_string(registry, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()

    def assert_columns():
        assert_db_columns(
            registry,
            "sale_order",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ],
        )

    def first():
        registry.register_model(SaleOrder)
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment(autocommit=True)
        assert_columns()

        so_1 = env["sale_order"].create({"name": "order 1"})
        so_2 = env["sale_order"].create({})

        assert so_1.name == "order 1"
        assert so_2.name is None

        so_2.name = "test"
        assert so_2.name == "test"

        so_1.name = "hello world"
        assert so_1.name == "hello world"

        with pytest.raises(SillyORMException) as e_info:
            so_1.name = 5
        assert str(e_info.value) == "String value must be str"

        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        registry.register_model(SaleOrder)
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment(autocommit=True)
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.name == "hello world"
        assert so_2.name == "test"

    if is_second:
        second()
    else:
        return first()


@with_test_registry(True)
def test_field_string_length(registry, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()
        test = sillyorm.fields.String(length=100)

    def assert_columns():
        assert_db_columns(
            registry,
            "sale_order",
            [
                ("id", sqlalchemy.sql.sqltypes.INTEGER()),
                ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
                ("test", sqlalchemy.sql.sqltypes.VARCHAR(length=100)),
            ],
        )

    def first():
        registry.register_model(SaleOrder)
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment(autocommit=True)
        assert_columns()

        so_1 = env["sale_order"].create({"name": "order 1", "test": "order 1 (test)"})
        so_2 = env["sale_order"].create({"test": "so 2"})

        assert so_1.name == "order 1"
        assert so_1.test == "order 1 (test)"
        assert so_2.name is None
        assert so_2.test == "so 2"

        return (so_1.id, so_2.id)

    def second():
        assert_columns()
        registry.register_model(SaleOrder)
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment(autocommit=True)
        assert_columns()
        so_1_id, so_2_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        assert so_1.name == "order 1"
        assert so_1.test == "order 1 (test)"
        assert so_2.name is None
        assert so_2.test == "so 2"
        so_1.name = None
        assert so_1.name is None

    if is_second:
        second()
    else:
        return first()
