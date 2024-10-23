import datetime
import sillyorm
from ..libtest import with_test_env, generic_field_test


@with_test_env(True)
def test_field_date(env, is_second, prev_return):
    return generic_field_test(
        sillyorm.fields.Date,
        [([], {})] * 4,
        [sillyorm.sql.SqlType.date()] * 4,
        [None, datetime.date(2024, 5, 7), datetime.date(2025, 5, 7), datetime.date(2023, 5, 7)],
        ["Test", [], {}, 1.5, datetime.datetime(2026, 5, 7)],
        env,
        is_second,
        prev_return,
    )
