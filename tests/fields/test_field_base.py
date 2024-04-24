import pytest
import sillyORM


def test_field_base():
    with pytest.raises(Exception) as e_info:
        class _(sillyORM.model.Model):
            _name = "sale_order"
            impossible = sillyORM.fields.Field()
    assert str(e_info.value) == "_sql_type must be set"
