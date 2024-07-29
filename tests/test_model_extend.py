import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_env, assert_db_columns


@with_test_env()
def test_model_extend(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        line_count = sillyorm.fields.Integer()
        line_count2 = sillyorm.fields.String()
        teststr = sillyorm.fields.String()

    class SaleOrderE1(sillyorm.model.Model):
        _extend = "sale_order"

        teststr = sillyorm.fields.String(length=123)
        newfield = sillyorm.fields.Integer()

    class SaleOrderE2(sillyorm.model.Model):
        _extend = "sale_order"

        line_count2 = sillyorm.fields.Integer()
        newfield = sillyorm.fields.String()

    def assert_columns():
        assert_db_columns(
            env.cr,
            "sale_order",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("line_count2", SqlType.integer()),
                ("teststr", SqlType.varchar(123)),
                ("newfield", SqlType.varchar(255)),
            ],
        )

    env.register_model(SaleOrder)
    env.register_model(SaleOrderE1)
    env.register_model(SaleOrderE2)
    env.init_tables()
    assert_columns()

    assert len(env["sale_order"].search([])) == 0

    so = env["sale_order"].create(
        {
            "line_count": 1,
            "line_count2": 6,
            "teststr": "this is a test string",
            "newfield": "this is another test string",
        }
    )
    assert so.line_count == 1
    assert so.line_count2 == 6
    assert so.teststr == "this is a test string"
    assert so.newfield == "this is another test string"

    so = env["sale_order"].create({})
    assert so.line_count is None
    assert so.line_count2 is None
    assert so.teststr is None
    assert so.newfield is None

    so.line_count = 3
    so.line_count2 = 4
    so.teststr = "bbbbb"
    so.newfield = "aaaaaa"
    assert so.line_count == 3
    assert so.line_count2 == 4
    assert so.teststr == "bbbbb"
    assert so.newfield == "aaaaaa"

    assert repr(env["sale_order"].search([])) == "sale_order[1, 2]"


@with_test_env()
def test_model_extend_invalid(env):
    class Invalid1(sillyorm.model.Model):
        pass

    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Invalid1)
    assert str(e_info.value) == "cannot register a model with neither _name or _extend set"

    class Invalid2(sillyorm.model.Model):
        _name = "a"
        _extend = "b"

    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Invalid2)
    assert str(e_info.value) == "cannot register a model with both _name and _extend set"

    class Invalid3(sillyorm.model.Model):
        _extend = "doesnotexist"

    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Invalid3)
    assert str(e_info.value) == "cannot extend nonexistant model 'doesnotexist'"
