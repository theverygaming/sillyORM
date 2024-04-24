import pytest
import sillyORM
from sillyORM.sql import SqlType
from sillyORM.tests.internal import with_test_env, assert_db_columns


@with_test_env
def test_field_many2one_one2many(env):
    class SaleOrder(sillyORM.model.Model):
        _name = "sale_order"

        name = sillyORM.fields.String()
        line_ids = sillyORM.fields.One2many("sale_order_line", "sale_order_id")

    class SaleOrderLine(sillyORM.model.Model):
        _name = "sale_order_line"

        product = sillyORM.fields.String()
        sale_order_id = sillyORM.fields.Many2one("sale_order")

    env.register_model(SaleOrder)
    env.register_model(SaleOrderLine)
    assert_db_columns(env.cr, "sale_order", [("id", SqlType.INTEGER), ("name", SqlType.VARCHAR)])
    assert_db_columns(env.cr, "sale_order_line", [("id", SqlType.INTEGER), ("product", SqlType.VARCHAR), ("sale_order_id", SqlType.INTEGER)])

    so_1_id = env["sale_order"].create({"name": "order 1"}).id
    so_2_id = env["sale_order"].create({"name": "order 2"}).id

    o1_l1 = env["sale_order_line"].create({"product": "p1 4 o1", "sale_order_id": so_1_id})
    o1_l2 = env["sale_order_line"].create({"product": "p2 4 o1", "sale_order_id": so_1_id})

    o2_l1 = env["sale_order_line"].create({"product": "p1 4 o2", "sale_order_id": so_2_id})
    o2_l2 = env["sale_order_line"].create({"product": "p2 4 o2", "sale_order_id": so_2_id})
    o2_l3 = env["sale_order_line"].create({"product": "p3 4 o2", "sale_order_id": so_2_id})

    assert isinstance(o1_l1.sale_order_id, SaleOrder)
    assert o1_l1.sale_order_id.id == so_1_id
    assert o1_l2.sale_order_id.id == so_1_id
    assert o2_l1.sale_order_id.id == so_2_id

    abandoned_so_line1 = env["sale_order_line"].create({"product": "p3 4 o2"})
    abandoned_so_line2 = env["sale_order_line"].create({"product": "p3 4 o2"})
    assert abandoned_so_line1.sale_order_id is None
    assert abandoned_so_line2.sale_order_id is None
    assert env["sale_order_line"].browse([abandoned_so_line1.id, abandoned_so_line2.id]).sale_order_id is None
    abandoned_so_line1.sale_order_id = env["sale_order"].browse(so_1_id)
    assert env["sale_order_line"].browse([abandoned_so_line1.id, abandoned_so_line2.id]).sale_order_id.id == so_1_id
    abandoned_so_line2.sale_order_id = env["sale_order"].browse(so_2_id)
    assert repr(env["sale_order_line"].browse([abandoned_so_line1.id, abandoned_so_line2.id]).sale_order_id) == f"sale_order[{so_1_id}, {so_2_id}]"

    # One2many
    assert repr(env["sale_order"].browse(so_1_id).line_ids) == f"sale_order_line[{o1_l1.id}, {o1_l2.id}, {abandoned_so_line1.id}]"
    assert repr(env["sale_order"].browse(so_2_id).line_ids) == f"sale_order_line[{o2_l1.id}, {o2_l2.id}, {o2_l3.id}, {abandoned_so_line2.id}]"

    with pytest.raises(NotImplementedError):
        env["sale_order"].browse(so_1_id).line_ids = 1
