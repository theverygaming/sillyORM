import re
import pytest
import psycopg2
import sillyORM
from sillyORM import SQLite, postgresql
from sillyORM.sql import SqlType, SqlConstraint

def pg_conn(tmp_path):
    dbname = re.sub('[^a-zA-Z0-9]', '', str(tmp_path))
    connstr = "host=127.0.0.1 user=postgres password=postgres"
    conn = psycopg2.connect(connstr + " dbname=postgres")
    conn.autocommit = True
    cr = conn.cursor()
    cr.execute(f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{dbname}';")
    if cr.fetchone() is None:
        cr.execute(f"CREATE DATABASE {dbname};")

    return postgresql.PostgreSQLConnection(connstr + f" dbname={dbname}")


def sqlite_conn(tmp_path):
    dbpath = tmp_path / "test.db"
    return SQLite.SQLiteConnection(dbpath)


def test_model_name():
    class TestModel(sillyORM.model.Model):
        test = sillyORM.fields.String()
    
    with pytest.raises(Exception) as e_info:
        TestModel(None, [])
    assert str(e_info.value) == "_name must be set"


def assert_db_columns(cr, table, columns):
    info = [(info.name, info.type) for info in cr.get_table_column_info(table)]
    assert len(info) == len(columns)
    for column in columns:
        assert column in info


def test_model_ids():
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
    
    model = TestModel(None, [])
    assert repr(model) == "test_model[]"
    with pytest.raises(Exception) as e_info:
        model.id
    assert str(e_info.value) == "ensure_one found 0 id's"
    assert [m.id for m in list(model)] == []

    model = TestModel(None, [1])
    assert repr(model) == "test_model[1]"
    assert model.id == 1
    assert [m.id for m in list(model)] == [1]

    model = TestModel(None, [1, 2, 3])
    assert repr(model) == "test_model[1, 2, 3]"
    with pytest.raises(Exception) as e_info:
        model.id
    assert str(e_info.value) == "ensure_one found 3 id's"
    assert [m.id for m in list(model)] == [1, 2, 3]


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_model_init(tmp_path, db_conn_fn):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()

    conn = db_conn_fn(tmp_path)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()
    
    conn = db_conn_fn(tmp_path)
    assert_db_columns(conn.cursor(), "test_model", [("id", SqlType.INTEGER), ("test", SqlType.VARCHAR)])
    conn.close()

    # now the database is initialized, do an update
    conn = db_conn_fn(tmp_path)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(conn.cursor(), "test_model", [("id", SqlType.INTEGER), ("test", SqlType.VARCHAR)])
    conn.close()


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_field_add_remove(tmp_path, db_conn_fn):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()

    class TestModel_extrafields(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    conn = db_conn_fn(tmp_path)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(conn.cursor(), "test_model", [("id", SqlType.INTEGER), ("test", SqlType.VARCHAR)])
    conn.close()

    # add new fields
    conn = db_conn_fn(tmp_path)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel_extrafields)
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(conn.cursor(), "test_model", [("id", SqlType.INTEGER), ("test", SqlType.VARCHAR), ("test2", SqlType.VARCHAR), ("test3", SqlType.VARCHAR)])
    conn.close()

    # remove the added fields again
    conn = db_conn_fn(tmp_path)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()

    conn = db_conn_fn(tmp_path)
    assert_db_columns(conn.cursor(), "test_model", [("id", SqlType.INTEGER), ("test", SqlType.VARCHAR)])
    conn.close()


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_create_browse(tmp_path, db_conn_fn):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    def new_env():
        env = sillyORM.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        return env

    env = new_env()
    r1 = env['test_model'].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env['test_model'].create({"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"})
    r3 = env['test_model'].create({"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"})
    assert r1.id == 1
    assert r2.id == 2
    assert r3.id == 3

    env = new_env()

    r12 = env['test_model'].browse([1, 2])
    assert r12.test == ["hello world!", "2 hello world!"]
    assert r12.test2 == ["test2", "2 test2"]
    assert r12.test3 == ["Hii!!", "2 Hii!!"]

    env = new_env()

    r2 = env['test_model'].browse(2)
    assert r2.id == 2
    assert r2.test == "2 hello world!"
    assert r2.test2 == "2 test2"
    assert r2.test3 == "2 Hii!!"

    env = new_env()

    assert env['test_model'].browse(15) is None


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_read(tmp_path, db_conn_fn):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    def new_env():
        env = sillyORM.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        return env

    env = new_env()
    r1 = env['test_model'].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env['test_model'].create({"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"})
    r3 = env['test_model'].create({"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"})
    assert r1.read(["test", "test2"]) == [{"test": "hello world!", "test2": "test2"}]
    assert r2.read(["test", "test3"]) == [{"test": "2 hello world!", "test3": "2 Hii!!"}]
    assert r3.read(["test", "test2"]) == [{"test": "3 hello world!", "test2": "3 test2"}]

    assert r2.read(["test2"]) == [{"test2": "2 test2"}]

    assert r1.test == "hello world!"
    assert r2.test2 == "2 test2"

    env = new_env()

    r12 = env['test_model'].browse([1, 2])
    assert r12.read(["test"]) == [{"test": "hello world!"}, {"test": "2 hello world!"}]
    assert r12.read(["test", "test3"]) == [{"test": "hello world!", "test3": "Hii!!"}, {"test": "2 hello world!", "test3": "2 Hii!!"}]


@pytest.mark.parametrize("db_conn_fn", [(sqlite_conn), (pg_conn)])
def test_write(tmp_path, db_conn_fn):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    def new_env():
        env = sillyORM.Environment(db_conn_fn(tmp_path).cursor())
        env.register_model(TestModel)
        return env

    env = new_env()
    r1 = env['test_model'].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env['test_model'].create({"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"})
    r3 = env['test_model'].create({"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"})

    r2_read_prev = r2.read(["test", "test2", "test3"])
    
    env = new_env()

    r13 = env['test_model'].browse([1, 3])

    r13_test2_prev = r13.test2

    r13.write({"test": "test field has been overwritten", "test3": "test3 field has been overwritten"})
    assert r13.test == ["test field has been overwritten", "test field has been overwritten"]
    assert r13_test2_prev == r13.test2
    assert r13.test3 == ["test3 field has been overwritten", "test3 field has been overwritten"]
    r3.test3 = "hello word r3"
    assert r13.test3 == ["test3 field has been overwritten", "hello word r3"]

    assert r2_read_prev == r2.read(["test", "test2", "test3"])
