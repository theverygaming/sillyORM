import sillyorm
import sqlalchemy
from ..libtest import with_test_registry, generic_field_test


@with_test_registry(True, with_request=True)
def test_field_large_binary(request, registry, is_second, prev_return):
    t = (
        sqlalchemy.dialects.postgresql.types.BYTEA
        if request.node.callspec.id == "PostgreSQL"
        else sqlalchemy.sql.sqltypes.BLOB
    )
    return generic_field_test(
        sillyorm.fields.LargeBinary,
        [([], {})] * 3,
        [t()] * 3,
        [b"hello", b"AAAAAAAAAAAAAAAAAAAaAAAAAAAAAAAAAAAAAAAAAAA", b"awrrruff,," * 1000000],
        ["Test", [], {}, 1.5, "2", 1, [1, 2]],
        registry,
        is_second,
        prev_return,
    )
