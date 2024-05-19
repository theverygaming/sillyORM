import pytest
import sillyorm
from sillyorm.exceptions import SillyORMException


def test_field_base():
    with pytest.raises(SillyORMException) as e_info:

        class _(sillyorm.model.Model):
            _name = "sale_order"
            impossible = sillyorm.fields.Field()

    assert str(e_info.value) == "sql_type must be set"
