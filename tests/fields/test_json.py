import datetime
import sillyorm
import sqlalchemy
from ..libtest import with_test_registry, generic_field_test


@with_test_registry(True, with_request=True)
def test_field_json(request, registry, is_second, prev_return):
    json_type = (
        sqlalchemy.dialects.postgresql.json.JSON
        if request.node.callspec.id == "PostgreSQL"
        else sqlalchemy.dialects.sqlite.json.JSON
    )
    return generic_field_test(
        sillyorm.fields.JSON,
        [([], {})] * 8,
        # none_as_null is False here even though it's actually True in the field
        # definition because inspecting from the DB this cannot be derived
        # (probably, at the time of writing I did not investigate further!!!)
        [json_type(none_as_null=False)] * 8,
        [
            "Test",
            [],
            {},
            1.5,
            1,
            {"1": 2, "2": [1, 2, 3]},
            [1, 2, 3, [4, 5], {"hii": None, "hewwo": 5}],
            None,
        ],
        [{1, 2, 3}, datetime.datetime.now(), lambda x: x, bytes([1, 2, 3])],
        registry,
        is_second,
        prev_return,
        invalid_write_vals_exc_type=sqlalchemy.exc.StatementError,
    )
