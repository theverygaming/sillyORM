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


@with_test_registry()
def test_registry_environment_invalidate(registry):
    class Model1(sillyorm.model.Model):
        _name = "a"

    registry.register_model(Model1)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    recordset = env["a"].create({})
    assert recordset.id == env["a"].browse(recordset.id).id
    registry.reset_full()
    registry.register_model(Model1)
    registry.resolve_tables()
    registry.init_db_tables()
    with pytest.raises(Exception):
        assert recordset.id == env["a"].browse(recordset.id).id
    with pytest.raises(Exception):
        env["a"].create({})
