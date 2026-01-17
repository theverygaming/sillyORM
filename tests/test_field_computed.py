import pytest
import sillyorm
from sillyorm.exceptions import SillyORMException
from .libtest import with_test_registry


@with_test_registry(False)
def test_field_computed(registry):
    class TestModel(sillyorm.model.Model):
        _name = "test_model"

        s1 = sillyorm.fields.String()
        s2 = sillyorm.fields.String(compute_fn="_compute_s2")
        s3 = sillyorm.fields.String(compute_fn="_compute_s3", compute_inverse_fn="_compute_inv_s3")

        def _compute_s2(self):
            return [str(r.s1) + " - computed s2" for r in self]

        def _compute_s3(self):
            return [str(r.s1) + " " + str(r.s1) for r in self]

        def _compute_inv_s3(self, value):
            self.s1 = value.split(" ")[0]

    registry.register_model(TestModel)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()

    rec1 = env["test_model"].create({"s1": "record1"})
    rec2 = env["test_model"].create({"s1": "record2"})
    rec3 = env["test_model"].create({"s1": "record3"})
    rec4 = env["test_model"].create({})

    # read, normal field
    assert rec1.s1 == "record1"
    assert rec2.s1 == "record2"
    assert rec3.s1 == "record3"
    assert rec4.s1 is None

    # read, first computed field (s2)
    assert rec1.s2 == "record1 - computed s2"
    assert rec2.s2 == "record2 - computed s2"
    assert rec3.s2 == "record3 - computed s2"
    assert rec4.s2 == "None - computed s2"

    # read, second computed field (s3)
    assert rec1.s3 == "record1 record1"
    assert rec2.s3 == "record2 record2"
    assert rec3.s3 == "record3 record3"
    assert rec4.s3 == "None None"

    # write, first computed field (s2)
    # should fail
    with pytest.raises(SillyORMException) as e_info:
        rec1.s2 = "test"
    assert str(e_info.value) == "field s2 cannot be written as it has no compute_inverse_fn method"

    # read, normal field
    # should be unchanged
    assert rec1.s1 == "record1"
    assert rec2.s1 == "record2"
    assert rec3.s1 == "record3"
    assert rec4.s1 is None

    # write, second computed field (s3)
    rec1.s3 = "hello hello"
    rec4.s3 = "4 4"

    # read, normal field
    # some should be changed by the inverse compute
    assert rec1.s1 == "hello"
    assert rec2.s1 == "record2"
    assert rec3.s1 == "record3"
    assert rec4.s1 == "4"
