import pytest
import sillyorm
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_registry, assert_db_columns


@with_test_registry()
def test_model_register_twice(registry):
    class Model1(sillyorm.model.Model):
        _name = "a"

    registry.register_model(Model1)
    with pytest.raises(SillyORMException) as e_info:
        registry.register_model(Model1)
    assert str(e_info.value) == "cannot register model 'a' twice"
