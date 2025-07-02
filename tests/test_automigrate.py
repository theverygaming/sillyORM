import pytest
import sillyorm
import sqlalchemy
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_registry, assert_db_columns


@with_test_registry()
def test_automigrate_safe(registry):
    class TestModelA(sillyorm.model.Model):
        _name = "test_model_a"

        name = sillyorm.fields.String()

    class TestModelB(sillyorm.model.Model):
        _name = "test_model_b"

        name = sillyorm.fields.String()
        value = sillyorm.fields.Integer()

    class TestModelA2(sillyorm.model.Model):
        _name = "test_model_a"

        name = sillyorm.fields.String(length=5)

    ## valid: add a table
    # init
    registry.register_model(TestModelA)
    registry.resolve_tables()
    registry.init_db_tables()
    assert_db_columns(
        registry,
        "test_model_a",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )
    # add table
    registry.register_model(TestModelB)
    registry.resolve_tables()
    registry.init_db_tables()
    assert_db_columns(
        registry,
        "test_model_a",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )
    assert_db_columns(
        registry,
        "test_model_b",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ("value", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )

    ## invalid: change a table
    registry.reset_full()
    registry.register_model(TestModelA2)
    registry.register_model(TestModelB)
    registry.resolve_tables()
    with pytest.raises(SillyORMException) as e_info:
        registry.init_db_tables()
    assert (
        str(e_info.value)
        == "The DB does not match the schema, things other than adding tables must be done and"
        " automigrate is set to 'safe' - diffs: [[('modify_type', None, 'test_model_a', 'name',"
        " {'existing_nullable': True, 'existing_server_default': False, 'existing_comment':"
        " None}, VARCHAR(length=255), String(length=5))]]"
    )

    ## invalid: remove a table
    registry.reset_full()
    registry.register_model(TestModelA)
    registry.resolve_tables()
    with pytest.raises(SillyORMException) as e_info:
        registry.init_db_tables()
    assert (
        str(e_info.value)
        == "The DB does not match the schema, things other than adding tables must be done and"
        " automigrate is set to 'safe' - diffs: [('remove_table', Table('test_model_b',"
        " MetaData(), Column('name', VARCHAR(length=255), table=<test_model_b>), Column('value',"
        " INTEGER(), table=<test_model_b>), Column('id', INTEGER(), table=<test_model_b>,"
        " primary_key=True, nullable=False), schema=None))]"
    )

    # After this, we should be able to init everything just fine
    registry.reset_full()
    registry.register_model(TestModelA)
    registry.register_model(TestModelB)
    registry.resolve_tables()
    registry.init_db_tables()
    assert_db_columns(
        registry,
        "test_model_a",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )
    assert_db_columns(
        registry,
        "test_model_b",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ("value", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )


@with_test_registry()
def test_automigrate_ignore(registry):
    class TestModelA(sillyorm.model.Model):
        _name = "test_model_a"

        name = sillyorm.fields.String()

    class TestModelA2(sillyorm.model.Model):
        _name = "test_model_a"

        name = sillyorm.fields.Integer()

    # init
    registry.register_model(TestModelA)
    registry.resolve_tables()
    registry.init_db_tables()
    assert_db_columns(
        registry,
        "test_model_a",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )
    # ignore changed table
    registry.reset_full()
    registry.register_model(TestModelA2)
    registry.resolve_tables()
    registry.init_db_tables(automigrate="ignore")
    assert_db_columns(
        registry,
        "test_model_a",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )


@with_test_registry()
def test_automigrate_none(registry):
    class TestModelA(sillyorm.model.Model):
        _name = "test_model_a"

        name = sillyorm.fields.String()

    class TestModelB(sillyorm.model.Model):
        _name = "test_model_b"

        name = sillyorm.fields.String()
        value = sillyorm.fields.Integer()

    # init
    registry.register_model(TestModelA)
    registry.resolve_tables()
    registry.init_db_tables()
    assert_db_columns(
        registry,
        "test_model_a",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )
    # error on added table
    registry.register_model(TestModelB)
    registry.resolve_tables()
    with pytest.raises(SillyORMException) as e_info:
        registry.init_db_tables(automigrate="none")
    assert (
        str(e_info.value)
        == "The DB does not match the schema and automigrate is set to 'none' - diffs:"
        " [('add_table', Table('test_model_b', MetaData(), Column('name', String(length=255),"
        " table=<test_model_b>), Column('value', Integer(), table=<test_model_b>), Column('id',"
        " Integer(), table=<test_model_b>, primary_key=True, nullable=False), schema=None))]"
    )
