import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns

_STRING_1MB = "a" * 1000000
_STRING_43MB = "the quick brown fox jumps over the lazy dog" * 1000000


@with_test_env(True)
def test_field_text(env, is_second, prev_return):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.Text()

    def assert_columns():
        assert_db_columns(
            env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.text())]
        )

    def first():
        env.register_model(SaleOrder)
        assert_columns()

        so_1 = env["sale_order"].create({"name": "order 1"})
        so_2 = env["sale_order"].create({})
        so_3 = env["sale_order"].create({"name": _STRING_1MB})

        assert so_1.name == "order 1"
        assert so_2.name is None
        strings_eq = so_3.name == _STRING_1MB
        string_len = len(so_3.name)
        assert strings_eq
        assert string_len == 1000000

        so_2.name = "test"
        assert so_2.name == "test"

        so_1.name = "hello world"
        assert so_1.name == "hello world"

        so_3.name = _STRING_43MB
        strings_eq = so_3.name == _STRING_43MB
        string_len = len(so_3.name)
        assert strings_eq
        assert string_len == 43000000

        with pytest.raises(SillyORMException) as e_info:
            so_1.name = 5
        assert str(e_info.value) == "Text value must be str"

        return (so_1.id, so_2.id, so_3.id)

    def second():
        assert_columns()
        env.register_model(SaleOrder)
        assert_columns()
        so_1_id, so_2_id, so_3_id = prev_return
        so_1 = env["sale_order"].browse(so_1_id)
        so_2 = env["sale_order"].browse(so_2_id)
        so_3 = env["sale_order"].browse(so_3_id)
        assert so_1.name == "hello world"
        assert so_2.name == "test"
        strings_eq = so_3.name == _STRING_43MB
        string_len = len(so_3.name)
        assert strings_eq
        assert string_len == 43000000

    if is_second:
        second()
    else:
        return first()
