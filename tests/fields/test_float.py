import sillyorm
import sqlalchemy
from ..libtest import with_test_registry, generic_field_test


@with_test_registry(True, with_request=True)
def test_field_float(request, registry, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Float,
        [([], {})] * 12,
        [
            (
                sqlalchemy.sql.sqltypes.DOUBLE_PRECISION(precision=53)
                if request.node.callspec.id == "PostgreSQL"
                else sqlalchemy.sql.sqltypes.FLOAT()
            )
        ]
        * 12,
        [
            None,
            123456.789012,
            340000000000000000000000000000000000000.0,
            -0.000000000000000000000000000000000000012,
            0.789012,
            123456.0,
            0,
            123,
            5,
            123456,
            -1,
            -123,
        ],
        ["Test", "2", "1.2", [], {}],
        registry,
        is_second,
        prev_return,
    )
