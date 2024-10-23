import sillyorm
from ..libtest import with_test_env, generic_field_test


@with_test_env(True)
def test_field_selection(env, is_second, prev_return):
    options = ["option1", "0", "1", "4option"]
    return generic_field_test(
        sillyorm.fields.Selection,
        [([options], {})] * 3 + [([options], {"length": 123})],
        [sillyorm.sql.SqlType.varchar(255)] * 3 + [sillyorm.sql.SqlType.varchar(123)],
        options,
        ["Test", [], {}, 1.5, "2", 1],
        env,
        is_second,
        prev_return,
    )
