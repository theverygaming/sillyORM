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

        def testfn(self):
            return f"SaleOrder"

    class SaleOrderE1(sillyorm.model.Model):
        _name = "sale_order"
        _extends = "sale_order"

        teststr = sillyorm.fields.String(length=123)
        newfield = sillyorm.fields.Integer()

        def testfn(self):
            ret = super().testfn()
            return f"{ret} SaleOrderE1"

    class SaleOrderE2(sillyorm.model.Model):
        _name = "sale_order"
        _extends = "sale_order"

        line_count2 = sillyorm.fields.Integer()
        newfield = sillyorm.fields.String()

        def testfn(self):
            ret = super().testfn()
            return f"{ret} SaleOrderE2"

    class PurchaseOrder(sillyorm.model.Model):
        _name = "purchase_order"
        _inherits = ["sale_order"]

        purchase_field = sillyorm.fields.String()

        def testfn(self):
            ret = super().testfn()
            return f"{ret} PurchaseOrder"

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

        assert_db_columns(
            env.cr,
            "purchase_order",
            [
                ("id", SqlType.integer()),
                ("line_count", SqlType.integer()),
                ("line_count2", SqlType.integer()),
                ("teststr", SqlType.varchar(123)),
                ("newfield", SqlType.varchar(255)),
                ("purchase_field", SqlType.varchar(255)),
            ],
        )

    env.register_model(SaleOrder)
    env.register_model(SaleOrderE1)
    env.register_model(SaleOrderE2)
    env.register_model(PurchaseOrder)
    env.init_tables()
    assert_columns()

    assert env["sale_order"]._name == "sale_order"
    assert env["purchase_order"]._name == "purchase_order"

    assert env["sale_order"].testfn() == "SaleOrder SaleOrderE1 SaleOrderE2"
    assert env["purchase_order"].testfn() == "SaleOrder SaleOrderE1 SaleOrderE2 PurchaseOrder"

    assert len(env["sale_order"].search([])) == 0
    assert len(env["purchase_order"].search([])) == 0

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

    po = env["purchase_order"].create(
        {
            "line_count": 1,
            "line_count2": 6,
            "teststr": "PO this is a test string",
            "newfield": "PO this is another test string",
            "purchase_field": "Some cool purchase order thing!",
        }
    )
    assert po.line_count == 1
    assert po.line_count2 == 6
    assert po.teststr == "PO this is a test string"
    assert po.newfield == "PO this is another test string"
    assert po.purchase_field == "Some cool purchase order thing!"

    so = env["sale_order"].create({})
    assert so.line_count is None
    assert so.line_count2 is None
    assert so.teststr is None
    assert so.newfield is None

    po = env["purchase_order"].create({})
    assert po.line_count is None
    assert po.line_count2 is None
    assert po.teststr is None
    assert po.newfield is None
    assert po.purchase_field is None

    so.line_count = 3
    so.line_count2 = 4
    so.teststr = "bbbbb"
    so.newfield = "aaaaaa"
    assert so.line_count == 3
    assert so.line_count2 == 4
    assert so.teststr == "bbbbb"
    assert so.newfield == "aaaaaa"

    po.line_count = 3
    po.line_count2 = 4
    po.teststr = "bbbbb PO"
    po.newfield = "aaaaaaPO!"
    assert po.line_count == 3
    assert po.line_count2 == 4
    assert po.teststr == "bbbbb PO"
    assert po.newfield == "aaaaaaPO!"

    assert repr(env["sale_order"].search([])) == "sale_order[1, 2]"
    assert repr(env["purchase_order"].search([])) == "purchase_order[1, 2]"


@with_test_env()
def test_model_extend_invalid(env):
    class Invalid1(sillyorm.model.Model):
        pass

    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Invalid1)
    assert (
        str(e_info.value)
        == "cannot register a model without _name set (in case of extension you also need to set"
        " _name, for inheritance reasons)"
    )

    class Invalid2(sillyorm.model.Model):
        _extends = "b"

    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Invalid2)
    assert (
        str(e_info.value)
        == "cannot register a model without _name set (in case of extension you also need to set"
        " _name, for inheritance reasons)"
    )

    class Invalid3(sillyorm.model.Model):
        _name = "doesnotexist"
        _extends = "doesnotexist"

    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Invalid3)
    assert str(e_info.value) == "cannot extend nonexistant model 'doesnotexist'"

    class Invalid4(sillyorm.model.Model):
        _name = "something_else"
        _extends = "doesnotexist"

    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Invalid4)
    assert str(e_info.value) == "_name must be equal to _extends"


@with_test_env()
def test_model_inherit_invalid(env):
    class CommonModel(sillyorm.model.Model):
        _name = "common_model"

        f1 = sillyorm.fields.String()

    class CommonModelExt(sillyorm.model.Model):
        _name = "common_model"
        _extends = "common_model"

        f2 = sillyorm.fields.String()

    class SomeOtherModel(sillyorm.model.Model):
        _name = "other_model"
        _inherits = ["common_model"]

        f3 = sillyorm.fields.String()

    class CommonModelExt2(sillyorm.model.Model):
        _name = "common_model"
        _extends = "common_model"
        _inherits = ["other_model"]

        f4 = sillyorm.fields.String()

    env.register_model(CommonModel)
    env.register_model(CommonModelExt)
    env.register_model(SomeOtherModel)
    env.register_model(CommonModelExt2)

    with pytest.raises(SillyORMException) as e_info:
        env.init_tables()
    assert (
        str(e_info.value)
        == "Circular dependency in model inheritance: 'common_model' - involved models:"
        " 'common_model, other_model'"
    )


@with_test_env()
def test_model_inherit_order(env):
    class CommonModel(sillyorm.model.Model):
        _name = "common_model"

        f1 = sillyorm.fields.String(length=1)

    class CommonModelExt(sillyorm.model.Model):
        _name = "common_model"
        _extends = "common_model"

        f1 = sillyorm.fields.String(length=2)

    class SomeOtherModel(sillyorm.model.Model):
        _name = "other_model"

        f1 = sillyorm.fields.String(length=3)

    class TestModel1(sillyorm.model.Model):
        _name = "test_model1"
        _inherits = ["common_model", "other_model"]

    class TestModel2(sillyorm.model.Model):
        _name = "test_model2"
        _inherits = ["other_model", "common_model"]

    class TestModel3(sillyorm.model.Model):
        _name = "test_model3"
        _inherits = ["common_model", "other_model"]

    class TestModel3Ext(sillyorm.model.Model):
        _name = "test_model3"
        _extends = "test_model3"
        _inherits = ["other_model", "common_model"]

    class TestModel4(sillyorm.model.Model):
        _name = "test_model4"
        _inherits = ["other_model", "common_model"]

        f1 = sillyorm.fields.String(length=123)

    class TestModel4Ext(sillyorm.model.Model):
        _name = "test_model4"
        _extends = "test_model4"
        _inherits = ["common_model", "other_model"]

    env.register_model(CommonModel)
    env.register_model(CommonModelExt)
    env.register_model(SomeOtherModel)
    env.register_model(TestModel1)
    env.register_model(TestModel2)
    env.register_model(TestModel3)
    env.register_model(TestModel3Ext)
    env.register_model(TestModel4)
    env.register_model(TestModel4Ext)
    env.init_tables()

    assert_db_columns(
        env.cr,
        "test_model1",
        [
            ("id", SqlType.integer()),
            ("f1", SqlType.varchar(3)),
        ],
    )

    assert_db_columns(
        env.cr,
        "test_model2",
        [
            ("id", SqlType.integer()),
            ("f1", SqlType.varchar(2)),
        ],
    )

    assert_db_columns(
        env.cr,
        "test_model3",
        [
            ("id", SqlType.integer()),
            ("f1", SqlType.varchar(2)),
        ],
    )

    assert_db_columns(
        env.cr,
        "test_model4",
        [
            ("id", SqlType.integer()),
            ("f1", SqlType.varchar(3)),
        ],
    )
