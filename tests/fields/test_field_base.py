import pytest
import sillyorm
from sillyorm.exceptions import SillyORMException


def test_field_base():
    with pytest.raises(SillyORMException) as e_info:

        class Sample(sillyorm.model.Model):
            _name = "sale_order"
            impossible = sillyorm.fields.Field()

        Sample._build_fields_list()

    assert str(e_info.value) == "sql_type must be set for all fields that materialize"
