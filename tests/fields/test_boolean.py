import sillyorm
import sqlalchemy
from ..libtest import with_test_registry, generic_field_test


@with_test_registry(True)
def test_field_boolean(registry, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Boolean,
        [([], {})] * 3,
        [sqlalchemy.sql.sqltypes.BOOLEAN()] * 3,
        [None, True, False],
        ["Test", [], {}, 1.5],
        registry,
        is_second,
        prev_return,
    )
