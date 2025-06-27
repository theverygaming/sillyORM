import sillyorm
import sqlalchemy
from ..libtest import with_test_registry, generic_field_test


@with_test_registry(True)
def test_field_selection(registry, is_second, prev_return):
    options = ["option1", "0", "1", "4option"]
    return generic_field_test(
        sillyorm.fields.Selection,
        [([options], {})] * 3 + [([options], {"length": 123})],
        [sqlalchemy.sql.sqltypes.VARCHAR(255)] * 3 + [sqlalchemy.sql.sqltypes.VARCHAR(123)],
        options,
        ["Test", [], {}, 1.5, "2", 1],
        registry,
        is_second,
        prev_return,
    )
