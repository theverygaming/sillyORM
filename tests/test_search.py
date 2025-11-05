import pytest
import datetime
import sillyorm
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_registry, assert_db_columns


@with_test_registry(False)
def test_search_none(registry):
    class Test(sillyorm.model.Model):
        _name = "test"

        s = sillyorm.fields.String()

    registry.register_model(Test)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()

    so_1 = env["test"].create({"s": "some value 1"})
    so_2 = env["test"].create({})
    so_3 = env["test"].create({"s": "some value 2"})
    so_4 = env["test"].create({})
    so_5 = env["test"].create({"s": "some value 3"})
    so_6 = env["test"].create({})

    assert env["test"].search([("s", "=", None)]).ids == [2, 4, 6]
    assert env["test"].search([("s", "=", None), "|", ("s", "=", "some value 2")]).ids == [
        2,
        3,
        4,
        6,
    ]


@with_test_registry(False)
def test_search_ilike(registry):
    class Test(sillyorm.model.Model):
        _name = "test"

        s = sillyorm.fields.String()

    registry.register_model(Test)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()

    so_1 = env["test"].create({"s": "bla bla uwu bla bla"})
    so_2 = env["test"].create({})
    so_3 = env["test"].create({"s": "bla bla uwu"})
    so_4 = env["test"].create({})
    so_5 = env["test"].create({"s": "uwu bla bla"})
    so_6 = env["test"].create({"s": "UwU bla bla"})
    so_7 = env["test"].create({"s": "helloAworld"})
    so_8 = env["test"].create({"s": "helloBworld"})
    so_9 = env["test"].create({"s": "helloABworld"})

    # Test %
    assert env["test"].search([("s", "ilike", "uwu")]).ids == [1, 3, 5, 6]
    assert env["test"].search([("s", "ilike", "UwU")]).ids == [1, 3, 5, 6]
    assert env["test"].search([("s", "=ilike", "uwu%")]).ids == [5, 6]
    assert env["test"].search([("s", "=ilike", "UwU%")]).ids == [5, 6]
    assert env["test"].search([("s", "=ilike", "Hello%World")]).ids == [7, 8, 9]

    # Test _
    assert env["test"].search([("s", "=ilike", "hello_world")]).ids == [7, 8]
    assert env["test"].search([("s", "=ilike", "Hello__world")]).ids == [9]

    # Test % and _ in an OR
    assert env["test"].search(
        [("s", "=ilike", "uwu%"), "|", ("s", "=ilike", "hello_world")]
    ).ids == [5, 6, 7, 8]


@with_test_registry(False)
def test_search_in(registry):
    class Test(sillyorm.model.Model):
        _name = "test"

        s = sillyorm.fields.String()

    registry.register_model(Test)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()

    so_1 = env["test"].create({"s": "meow"})
    so_2 = env["test"].create({})
    so_3 = env["test"].create({"s": "waff"})
    so_4 = env["test"].create({})
    so_5 = env["test"].create({"s": "bark"})
    so_6 = env["test"].create({"s": "awoo!"})

    # normal
    assert set(env["test"].search([("s", "in", ["meow", "waff"])]).ids) == {so_1.id, so_3.id}

    # with None
    assert set(env["test"].search([("s", "in", ["meow", "awoo!", None])]).ids) == {
        so_1.id,
        so_6.id,
        so_2.id,
        so_4.id,
    }

    # combination with other stuff
    assert set(
        env["test"].search([("s", "in", ["meow", "bark"]), "|", ("s", "=", "awoo!")]).ids
    ) == {so_1.id, so_5.id, so_6.id}
