import pytest
import sillyorm
import sqlalchemy
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_registry, assert_db_columns


@with_test_registry()
def test_field_many2one_one2many(registry):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()
        line_ids = sillyorm.fields.One2many("sale_order_line", "sale_order_id")

    class SaleOrderLine(sillyorm.model.Model):
        _name = "sale_order_line"

        product = sillyorm.fields.String()
        sale_order_id = sillyorm.fields.Many2one("sale_order")

    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderLine)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        registry,
        "sale_order",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )
    assert_db_columns(
        registry,
        "sale_order_line",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("product", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
            ("sale_order_id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )

    so_1_id = env["sale_order"].create({"name": "order 1"}).id
    so_2_id = env["sale_order"].create({"name": "order 2"}).id

    o1_l1 = env["sale_order_line"].create({"product": "p1 4 o1", "sale_order_id": so_1_id})
    o1_l2 = env["sale_order_line"].create({"product": "p2 4 o1", "sale_order_id": so_1_id})

    o2_l1 = env["sale_order_line"].create({"product": "p1 4 o2", "sale_order_id": so_2_id})
    o2_l2 = env["sale_order_line"].create({"product": "p2 4 o2", "sale_order_id": so_2_id})
    o2_l3 = env["sale_order_line"].create({"product": "p3 4 o2", "sale_order_id": so_2_id})
    o2_l4 = env["sale_order_line"].create({"product": "p3 4 o2", "sale_order_id": None})

    assert isinstance(o1_l1.sale_order_id, SaleOrder)
    assert o1_l1.sale_order_id.id == so_1_id
    assert o1_l2.sale_order_id.id == so_1_id
    assert o2_l1.sale_order_id.id == so_2_id

    assert o2_l4.sale_order_id is None
    o2_l4.sale_order_id = env["sale_order"].browse(so_1_id)
    assert o2_l4.sale_order_id.id is so_1_id
    o2_l4.sale_order_id = None
    assert o2_l4.sale_order_id is None

    abandoned_so_line1 = env["sale_order_line"].create({"product": "p3 4 o2"})
    abandoned_so_line2 = env["sale_order_line"].create({"product": "p3 4 o2"})
    assert abandoned_so_line1.sale_order_id is None
    assert abandoned_so_line2.sale_order_id is None
    abandoned_so_line1.sale_order_id = env["sale_order"].browse(so_1_id)

    with pytest.raises(SillyORMException) as e_info:
        env["sale_order_line"].browse(
            [abandoned_so_line1.id, abandoned_so_line2.id]
        ).sale_order_id.id
    assert str(e_info.value) == "ensure_one found 2 id's"

    abandoned_so_line2.sale_order_id = env["sale_order"].browse(so_2_id)
    with pytest.raises(SillyORMException) as e_info:
        env["sale_order_line"].browse([abandoned_so_line1.id, abandoned_so_line2.id]).sale_order_id
    assert str(e_info.value) == "ensure_one found 2 id's"

    assert env["sale_order_line"].browse([abandoned_so_line1.id]).sale_order_id.id == so_1_id

    # One2many
    assert (
        repr(env["sale_order"].browse(so_1_id).line_ids)
        == f"sale_order_line[{o1_l1.id}, {o1_l2.id}, {abandoned_so_line1.id}]"
    )
    assert (
        repr(env["sale_order"].browse(so_2_id).line_ids)
        == f"sale_order_line[{o2_l1.id}, {o2_l2.id}, {o2_l3.id}, {abandoned_so_line2.id}]"
    )

    with pytest.raises(NotImplementedError):
        env["sale_order"].browse(so_1_id).line_ids = 1
