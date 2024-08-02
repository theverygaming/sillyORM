import sillyorm
from ..libtest import with_test_env, generic_field_test


@with_test_env(True)
def test_field_float(env, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Float,
        [([], {})] * 6,
        [
            None,
            123456.789012,
            340000000000000000000000000000000000000.0,
            -0.000000000000000000000000000000000000012,
            0.789012,
            123456.0,
        ],
        ["Test", [], {}, 3, -1],
        env,
        is_second,
        prev_return,
    )
