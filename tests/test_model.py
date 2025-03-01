import re
import pytest
import psycopg2
import sillyorm
from sillyorm.dbms import sqlite
from sillyorm.dbms import postgresql
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from .libtest import assert_db_columns


def pg_conn(tmp_path):
    dbname = f"pytestdb{hash(str(tmp_path))}"
    connstr = "host=127.0.0.1 user=postgres password=postgres"
    conn = psycopg2.connect(connstr + " dbname=postgres")
    conn.autocommit = True
    cr = conn.cursor()
    cr.execute(f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{dbname}';")
    if cr.fetchone() is None:
        cr.execute(f'CREATE DATABASE "{dbname}";')

    return postgresql.PostgreSQLConnection(connstr + f" dbname={dbname}")


def sqlite_conn(tmp_path):
    dbpath = tmp_path / "test.db"
    return sqlite.SQLiteConnection(dbpath)


def test_model_name():
    class TestModel(sillyorm.model.Model):
        test = sillyorm.fields.String()

    with pytest.raises(SillyORMException) as e_info:
        TestModel(None, [])
    assert str(e_info.value) == "_name or _extends must be set"


def test_model_ids():
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()

    model = TestModel(None, [])
    assert repr(model) == "test_model[]"
    with pytest.raises(SillyORMException) as e_info:
        model.id
    assert str(e_info.value) == "ensure_one found 0 id's"
    assert [m.id for m in list(model)] == []

    model = TestModel(None, [1])
    assert repr(model) == "test_model[1]"
    assert model.id == 1
    assert [m.id for m in list(model)] == [1]

    model = TestModel(None, [1, 2, 3])
    assert repr(model) == "test_model[1, 2, 3]"
    with pytest.raises(SillyORMException) as e_info:
        model.id
    assert str(e_info.value) == "ensure_one found 3 id's"
    assert [m.id for m in list(model)] == [1, 2, 3]


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_model_init(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()

    conn = db_conn_fn(tmp_path)
    env = sillyorm.Environment(conn.cursor())
    env.register_model(TestModel)
    env.init_tables()
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(
        conn.cursor(), "test_model", [("id", SqlType.integer()), ("test", SqlType.varchar(255))]
    )
    conn.close()

    # now the database is initialized, do an update
    conn = db_conn_fn(tmp_path)
    env = sillyorm.Environment(conn.cursor())
    env.register_model(TestModel)
    env.init_tables()
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(
        conn.cursor(), "test_model", [("id", SqlType.integer()), ("test", SqlType.varchar(255))]
    )
    conn.close()


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_field_add_remove(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()

    class TestModel_extrafields(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()
        test3 = sillyorm.fields.String()

    conn = db_conn_fn(tmp_path)
    env = sillyorm.Environment(conn.cursor())
    env.register_model(TestModel)
    env.init_tables()
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(
        conn.cursor(), "test_model", [("id", SqlType.integer()), ("test", SqlType.varchar(255))]
    )
    conn.close()

    # add new fields
    conn = db_conn_fn(tmp_path)
    env = sillyorm.Environment(conn.cursor())
    env.register_model(TestModel_extrafields)
    env.init_tables()
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(
        conn.cursor(),
        "test_model",
        [
            ("id", SqlType.integer()),
            ("test", SqlType.varchar(255)),
            ("test2", SqlType.varchar(255)),
            ("test3", SqlType.varchar(255)),
        ],
    )
    conn.close()

    # remove the added fields again
    conn = db_conn_fn(tmp_path)
    env = sillyorm.Environment(conn.cursor())
    env.register_model(TestModel)
    env.init_tables()
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(
        conn.cursor(), "test_model", [("id", SqlType.integer()), ("test", SqlType.varchar(255))]
    )
    conn.close()


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_create_browse(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()
        test3 = sillyorm.fields.String()

    def new_env():
        env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        env.init_tables()
        return env

    env = new_env()
    r1 = env["test_model"].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env["test_model"].create(
        {"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"}
    )
    r3 = env["test_model"].create(
        {"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"}
    )
    assert r1.id == 1
    assert r2.id == 2
    assert r3.id == 3

    env = new_env()

    r12 = env["test_model"].browse([1, 2])
    with pytest.raises(SillyORMException) as e_info:
        r12.test
    assert str(e_info.value) == "ensure_one found 2 id's"
    with pytest.raises(SillyORMException) as e_info:
        r12.test2
    assert str(e_info.value) == "ensure_one found 2 id's"
    with pytest.raises(SillyORMException) as e_info:
        r12.test3
    assert str(e_info.value) == "ensure_one found 2 id's"

    env = new_env()

    r2 = env["test_model"].browse(2)
    assert r2.id == 2
    assert r2.test == "2 hello world!"
    assert r2.test2 == "2 test2"
    assert r2.test3 == "2 Hii!!"

    env = new_env()

    assert env["test_model"].browse(15) is None


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_read(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()
        test3 = sillyorm.fields.String()

    def new_env():
        env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        env.init_tables()
        return env

    env = new_env()
    r1 = env["test_model"].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env["test_model"].create(
        {"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"}
    )
    r3 = env["test_model"].create(
        {"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"}
    )
    assert r1.read(["test", "test2"]) == [{"test": "hello world!", "test2": "test2"}]
    assert r2.read(["test", "test3"]) == [{"test": "2 hello world!", "test3": "2 Hii!!"}]
    assert r3.read(["test", "test2"]) == [{"test": "3 hello world!", "test2": "3 test2"}]

    assert r2.read(["test2"]) == [{"test2": "2 test2"}]

    assert r1.test == "hello world!"
    assert r2.test2 == "2 test2"

    env = new_env()

    r12 = env["test_model"].browse([1, 2])
    assert r12.read(["test"]) == [{"test": "hello world!"}, {"test": "2 hello world!"}]
    assert r12.read(["test", "test3"]) == [
        {"test": "hello world!", "test3": "Hii!!"},
        {"test": "2 hello world!", "test3": "2 Hii!!"},
    ]


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_write(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()
        test3 = sillyorm.fields.String()

    def new_env():
        env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        env.init_tables()
        return env

    env = new_env()
    r1 = env["test_model"].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env["test_model"].create(
        {"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"}
    )
    r3 = env["test_model"].create(
        {"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"}
    )

    r2_read_prev = r2.read(["test", "test2", "test3"])

    env = new_env()

    r13 = env["test_model"].browse([1, 3])

    r13_test2_prev = r13.read(["test2"])

    r13.write(
        {"test": "test field has been overwritten", "test3": "test3 field has been overwritten"}
    )
    assert r13.read(["test"]) == [
        {"test": "test field has been overwritten"},
        {"test": "test field has been overwritten"},
    ]
    assert r13_test2_prev == r13.read(["test2"])
    assert r13.read(["test3"]) == [
        {"test3": "test3 field has been overwritten"},
        {"test3": "test3 field has been overwritten"},
    ]
    r3.test3 = "hello word r3"
    assert r13.read(["test3"]) == [
        {"test3": "test3 field has been overwritten"},
        {"test3": "hello word r3"},
    ]

    assert r2_read_prev == r2.read(["test", "test2", "test3"])


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_search(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()
        test3 = sillyorm.fields.String()

    def new_env():
        env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        env.init_tables()
        return env

    env = new_env()
    r1 = env["test_model"].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env["test_model"].create(
        {"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"}
    )
    r3 = env["test_model"].create(
        {"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"}
    )
    assert r1.id == 1
    assert r2.id == 2
    assert r3.id == 3

    env = new_env()

    r13_domain = [("test2", "=", "test2"), "|", ("test3", "=", "3 Hii!!")]
    assert env["test_model"].search_count(r13_domain) == 2
    r13 = env["test_model"].search(r13_domain)
    assert sorted(r13._ids) == [1, 3]

    env = new_env()

    assert env["test_model"].search_count([]) == 3
    assert env["test_model"].search([])._ids == [1, 2, 3]

    # test limit & offset
    assert env["test_model"].search([], limit=1)._ids == [1]
    assert env["test_model"].search([], limit=2)._ids == [1, 2]
    assert env["test_model"].search([], limit=2, offset=1)._ids == [2, 3]
    assert env["test_model"].search([], limit=10, offset=2)._ids == [3]
    assert env["test_model"].search([], limit=1, offset=3)._ids == []

    # test order by
    assert env["test_model"].search([], order_by="id")._ids == [1, 2, 3]
    assert env["test_model"].search([], order_by="id", order_asc=False)._ids == [3, 2, 1]
    assert env["test_model"].search([], order_by="id", order_asc=True)._ids == [1, 2, 3]
    assert env["test_model"].search([], order_by="test", order_asc=True)._ids == [2, 3, 1]
    assert env["test_model"].search([], order_by="test", order_asc=False)._ids == [1, 3, 2]

    # test order by, together with limit & offset AND a domain
    assert env["test_model"].search([("id", "<", 3)], order_by="test", order_asc=True)._ids == [
        2,
        1,
    ]
    assert env["test_model"].search(
        [("id", "<", 3)], order_by="test", order_asc=True, limit=1, offset=1
    )._ids == [1]
    assert env["test_model"].search([("id", "<", 3)], order_by="test", order_asc=False)._ids == [
        1,
        2,
    ]
    assert env["test_model"].search(
        [("id", "<", 3)], order_by="test", order_asc=False, limit=1, offset=1
    )._ids == [2]

    domain_r2 = [
        "(",
        ("test2", "=", "test2"),
        "&",
        ("test", "=", "hello world!"),
        ")",
        "|",
        ("test2", "=", "2 Hii!!"),
    ]
    assert env["test_model"].search_count(domain_r2) == 1
    r2 = env["test_model"].search(domain_r2)
    assert r2._ids == [1]

    env = new_env()

    assert (
        len(
            env["test_model"].search(
                [
                    "(",
                    ("test2", "=", "test2"),
                    "&",
                    ("test", "=", "hello world!"),
                    ")",
                    "&",
                    ("test2", "=", "2 Hii!!"),
                ]
            )
        )
        == 0
    )


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_search_2(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()
        test3 = sillyorm.fields.String()

    def new_env():
        env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        env.init_tables()
        return env

    env = new_env()
    r1 = env["test_model"].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env["test_model"].create(
        {"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"}
    )
    r3 = env["test_model"].create(
        {"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"}
    )
    r4 = env["test_model"].create(
        {"test": "4 hello world!", "test2": "4 test2", "test3": "4 Hii!!"}
    )
    r5 = env["test_model"].create(
        {"test": "5 hello world!", "test2": "5 test2", "test3": "5 Hii!!"}
    )
    assert r1.id == 1
    assert r2.id == 2
    assert r3.id == 3
    assert r4.id == 4
    assert r5.id == 5

    env = new_env()

    assert env["test_model"].search([])._ids == [1, 2, 3, 4, 5]

    env["test_model"].browse([1, 2]).delete()

    assert env["test_model"].search([])._ids == [3, 4, 5]

    env["test_model"].browse(3).delete()

    assert env["test_model"].search([])._ids == [4, 5]

    env = new_env()

    assert env["test_model"].search([])._ids == [4, 5]

    r6 = env["test_model"].create(
        {"test": "6 hello world!", "test2": "6 test2", "test3": "6 Hii!!"}
    )
    assert r6.id == 6

    assert env["test_model"].search([])._ids == [4, 5, 6]

    env = new_env()

    assert env["test_model"].search([])._ids == [4, 5, 6]

    env["test_model"].search([]).delete()

    assert len(env["test_model"].search([])) == 0

    env = new_env()

    assert len(env["test_model"].search([])) == 0


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_read_order(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()

    env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
    env.register_model(TestModel)
    env.init_tables()

    r1 = env["test_model"].create({"test": "a", "test2": "z"})
    r2 = env["test_model"].create({"test": "b", "test2": "y"})
    r3 = env["test_model"].create({"test": "c", "test2": "x"})
    assert r1.id == 1
    assert r2.id == 2
    assert r3.id == 3

    # Check if id orders returned by search are as expected
    assert env["test_model"].search([], order_by="id")._ids == [1, 2, 3]
    assert env["test_model"].search([], order_by="test")._ids == [1, 2, 3]
    assert env["test_model"].search([], order_by="test2")._ids == [3, 2, 1]

    # Check for the actual problem
    assert env["test_model"].search([], order_by="test").read(["test"]) == [
        {"test": "a"},
        {"test": "b"},
        {"test": "c"},
    ]
    assert env["test_model"].search([], order_by="test2").read(["test"]) == [
        {"test": "c"},
        {"test": "b"},
        {"test": "a"},
    ]

    # Check if our fix conflicts with limit/offset
    assert env["test_model"].search([], order_by="test", limit=2, offset=0).read(["test"]) == [
        {"test": "a"},
        {"test": "b"},
    ]
    assert env["test_model"].search([], order_by="test2", limit=2, offset=0).read(["test"]) == [
        {"test": "c"},
        {"test": "b"},
    ]
    assert env["test_model"].search([], order_by="test", limit=2, offset=1).read(["test"]) == [
        {"test": "b"},
        {"test": "c"},
    ]
    assert env["test_model"].search([], order_by="test2", limit=2, offset=1).read(["test"]) == [
        {"test": "b"},
        {"test": "a"},
    ]
    assert env["test_model"].search([], order_by="test", limit=2, offset=2).read(["test"]) == [
        {"test": "c"}
    ]
    assert env["test_model"].search([], order_by="test2", limit=2, offset=2).read(["test"]) == [
        {"test": "a"}
    ]


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_read_empty_recordset(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()
        test2 = sillyorm.fields.String()

    env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
    env.register_model(TestModel)
    env.init_tables()

    assert env["test_model"].search([]).read(["test"]) == []
    assert env["test_model"].search([], order_by="test2", limit=2, offset=0).read(["test"]) == []


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_model_subscript(tmp_path, db_conn_fn):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        test = sillyorm.fields.String()

    env = sillyorm.Environment(db_conn_fn(tmp_path).cursor())
    env.register_model(TestModel)
    env.init_tables()

    assert env["test_model"].search([])._ids == []
    with pytest.raises(IndexError):
        env["test_model"].search([])[0]

    env["test_model"].create({"test": "a"})

    assert env["test_model"].search([])._ids == [1]
    assert env["test_model"].search([])[0]._ids == [1]

    env["test_model"].create({"test": "b"})
    assert env["test_model"].search([])._ids == [1, 2]
    assert env["test_model"].search([])[0]._ids == [1]
    assert env["test_model"].search([])[1]._ids == [2]

    env["test_model"].create({"test": "c"})
    assert env["test_model"].search([])._ids == [1, 2, 3]
    assert env["test_model"].search([])[0]._ids == [1]
    assert env["test_model"].search([])[1]._ids == [2]
    assert env["test_model"].search([])[2]._ids == [3]
