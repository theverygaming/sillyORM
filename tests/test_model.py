import pytest
import sillyORM
from sillyORM import SQLite


# TODO: test with multiple DB backends

def test_model_name():
    class TestModel(sillyORM.model.Model):
        test = sillyORM.fields.String()
    
    with pytest.raises(Exception) as e_info:
        TestModel(None, [])
    assert str(e_info.value) == "_name must be set"


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


def test_model_init(tmp_path):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
    
    dbpath = tmp_path / "test.db"

    conn = SQLite.SQLiteConnection(dbpath)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()

    # TODO: check db tables

    # now the database is initialized, do an update
    conn = SQLite.SQLiteConnection(dbpath)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()

    # TODO: check db tables


def test_field_add_remove(tmp_path):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()

    class TestModel_extrafields(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    dbpath = tmp_path / "test.db"

    conn = SQLite.SQLiteConnection(dbpath)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()

    # add new fields
    conn = SQLite.SQLiteConnection(dbpath)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel_extrafields)
    conn.close()

    # TODO: check db tables

    # remove the added fields again
    conn = SQLite.SQLiteConnection(dbpath)
    env = sillyORM.Environment(conn.cursor())
    env.register_model(TestModel)
    conn.close()

    # TODO: check db tables


def test_create_browse(tmp_path):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    dbpath = tmp_path / "test.db"

    env = sillyORM.Environment(SQLite.SQLiteConnection(dbpath).cursor())
    env.register_model(TestModel)
    r1 = env['test_model'].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env['test_model'].create({"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"})
    r3 = env['test_model'].create({"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"})
    assert r1.id == 1
    assert r2.id == 2
    assert r3.id == 3

    r12 = env['test_model'].browse([1, 2])
    assert r12.test == ["hello world!", "2 hello world!"]
    assert r12.test2 == ["test2", "2 test2"]
    assert r12.test3 == ["Hii!!", "2 Hii!!"]

    r2 = env['test_model'].browse(2)
    assert r2.id == 2
    assert r2.test == "2 hello world!"
    assert r2.test2 == "2 test2"
    assert r2.test3 == "2 Hii!!"

    assert env['test_model'].browse(15) is None


def test_read(tmp_path):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    dbpath = tmp_path / "test.db"

    env = sillyORM.Environment(SQLite.SQLiteConnection(dbpath).cursor())
    env.register_model(TestModel)
    r1 = env['test_model'].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env['test_model'].create({"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"})
    r3 = env['test_model'].create({"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"})
    assert r1.read(["test", "test2"]) == [{"test": "hello world!", "test2": "test2"}]
    assert r2.read(["test", "test3"]) == [{"test": "2 hello world!", "test3": "2 Hii!!"}]
    assert r3.read(["test", "test2"]) == [{"test": "3 hello world!", "test2": "3 test2"}]

    assert r2.read(["test2"]) == [{"test2": "2 test2"}]

    assert r1.test == "hello world!"
    assert r2.test2 == "2 test2"

    r12 = env['test_model'].browse([1, 2])
    assert r12.read(["test"]) == [{"test": "hello world!"}, {"test": "2 hello world!"}]
    assert r12.read(["test", "test3"]) == [{"test": "hello world!", "test3": "Hii!!"}, {"test": "2 hello world!", "test3": "2 Hii!!"}]


def test_write(tmp_path):
    class TestModel(sillyORM.model.Model):
        _name = "test_model"

        test = sillyORM.fields.String()
        test2 = sillyORM.fields.String()
        test3 = sillyORM.fields.String()

    dbpath = tmp_path / "test.db"

    env = sillyORM.Environment(SQLite.SQLiteConnection(dbpath).cursor())
    env.register_model(TestModel)
    r1 = env['test_model'].create({"test": "hello world!", "test2": "test2", "test3": "Hii!!"})
    r2 = env['test_model'].create({"test": "2 hello world!", "test2": "2 test2", "test3": "2 Hii!!"})
    r3 = env['test_model'].create({"test": "3 hello world!", "test2": "3 test2", "test3": "3 Hii!!"})
    

    r2_read_prev = r2.read(["test", "test2", "test3"])
    
    r13 = env['test_model'].browse([1, 3])

    r13_test2_prev = r13.test2

    r13.write({"test": "test field has been overwritten", "test3": "test3 field has been overwritten"})
    assert r13.test == ["test field has been overwritten", "test field has been overwritten"]
    assert r13_test2_prev == r13.test2
    assert r13.test3 == ["test3 field has been overwritten", "test3 field has been overwritten"]
    r3.test3 = "hello word r3"
    assert r13.test3 == ["test3 field has been overwritten", "hello word r3"]

    assert r2_read_prev == r2.read(["test", "test2", "test3"])
