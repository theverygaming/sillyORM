import pytest
import datetime
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_env, assert_db_columns


@with_test_env(False)
def test_search_none(env):
    class Test(sillyorm.model.Model):
        _name = "test"

        s = sillyorm.fields.String()

    env.register_model(Test)
    env.init_tables()

    so_1 = env["test"].create({"s": "some value 1"})
    so_2 = env["test"].create({})
    so_3 = env["test"].create({"s": "some value 2"})
    so_4 = env["test"].create({})
    so_5 = env["test"].create({"s": "some value 3"})
    so_6 = env["test"].create({})

    assert env["test"].search([("s", "=", None)])._ids == [2, 4, 6]
    assert env["test"].search([("s", "=", None), "|", ("s", "=", "some value 2")])._ids == [
        2,
        3,
        4,
        6,
    ]
