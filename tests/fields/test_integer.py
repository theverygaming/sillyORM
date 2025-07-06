import sillyorm
import sqlalchemy
from ..libtest import with_test_registry, generic_field_test


@with_test_registry(True)
def test_field_integer(registry, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Integer,
        [([], {})] * 6,
        [sqlalchemy.sql.sqltypes.INTEGER()] * 6,
        [
            None,
            5,
            32767,
            -32768,
            -1,
            6,
        ],
        ["Test", [], {}, 1.5],
        registry,
        is_second,
        prev_return,
    )
