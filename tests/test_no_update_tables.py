import pytest
import sillyorm
import sqlalchemy
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_registry, assert_db_columns


@pytest.mark.skip(
    reason="the DB layout stuff changed ever since we added sqlalchemy"
)  # TODO: add DB layout assertion
@with_test_registry()
def test_no_update_tables(registry):
    class SaleOrder1(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()

    class SaleOrder2(sillyorm.model.Model):
        _name = "sale_order"

    class SaleOrder3(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String(length=1312)

    class SaleOrder4(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String(length=123)

    ## add a table
    registry.register_model(SaleOrder1)
    # env.update_tables = False
    with pytest.raises(SillyORMException) as e_info:
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment()
    assert (
        str(e_info.value)
        == "no_update (table: 'sale_order'): would need to create a table 'sale_order' with columns"
        ' \'[SQL("name" VARCHAR(255)), SQL("id" INTEGER), SQL(PRIMARY KEY ("id"))]\''
    )
    # env.update_tables = True
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(255))]
    )
    del env._models["sale_order"]  # remove so we can register the model again
    del env._lmodels["sale_order"]  # remove so we can register the model again

    ## remove a field
    registry.register_model(SaleOrder2)
    # env.update_tables = False
    with pytest.raises(SillyORMException) as e_info:
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment()
    assert (
        str(e_info.value)
        == "no_update (table: 'sale_order'): would need to remove columns '[ColumnInfo(name='name',"
        " type=<SqlType VARCHAR(255)>, constraints=[])]'"
    )
    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(255))]
    )
    # env.update_tables = True
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.integer())])
    del env._models["sale_order"]  # remove so we can register the model again
    del env._lmodels["sale_order"]  # remove so we can register the model again

    ## add a field
    registry.register_model(SaleOrder3)
    # env.update_tables = False
    with pytest.raises(SillyORMException) as e_info:
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment()
    assert (
        str(e_info.value)
        == "no_update (table: 'sale_order'): would need to add columns '[ColumnInfo(name='name',"
        " type=<SqlType VARCHAR(1312)>, constraints=[])]'"
    )
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.integer())])
    # env.update_tables = True
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(1312))]
    )
    del env._models["sale_order"]  # remove so we can register the model again
    del env._lmodels["sale_order"]  # remove so we can register the model again

    ## change field type
    registry.register_model(SaleOrder4)
    # env.update_tables = False
    with pytest.raises(SillyORMException) as e_info:
        registry.resolve_tables()
        registry.init_db_tables()
        env = registry.get_environment()
    assert (
        str(e_info.value)
        == "no_update (table: 'sale_order'): would need to remove columns '[ColumnInfo(name='name',"
        " type=<SqlType VARCHAR(1312)>, constraints=[])]'"
    )
    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(1312))]
    )
    # env.update_tables = True
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(123))]
    )
    del env._models["sale_order"]  # remove so we can register the model again
    del env._lmodels["sale_order"]  # remove so we can register the model again

    # TODO: add a constraint (we don't quite support them yet sooo...)
