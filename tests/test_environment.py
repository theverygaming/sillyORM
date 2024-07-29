import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_env, assert_db_columns


@with_test_env()
def test_model_register_twice(env):
    class Model1(sillyorm.model.Model):
        _name = "a"

    env.register_model(Model1)
    with pytest.raises(SillyORMException) as e_info:
        env.register_model(Model1)
    assert str(e_info.value) == "cannot register model 'a' twice"
