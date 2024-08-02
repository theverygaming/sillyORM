import sillyorm
from ..libtest import with_test_env, generic_field_test


@with_test_env(True)
def test_field_boolean(env, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Boolean,
        [([], {})] * 3,
        [None, True, False],
        ["Test", [], {}, 1.5],
        env,
        is_second,
        prev_return,
    )
