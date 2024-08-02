import sillyorm
from ..libtest import with_test_env, generic_field_test


@with_test_env(True)
def test_field_integer(env, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Integer,
        [([], {})] * 6,
        [
            None,
            5,
            32767,
            -32768,
            -1,
            6,
        ],
        ["Test", [], {}, 1.5],
        env,
        is_second,
        prev_return,
    )
