import pytest
import sillyorm
from sillyorm.sql import SqlType
from sillyorm.exceptions import SillyORMException
from ..libtest import with_test_env, assert_db_columns


@with_test_env()
def test_field_many2one_one2many(env):
    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

        name = sillyorm.fields.String()
        line_ids = sillyorm.fields.One2many("sale_order_line", "sale_order_id")

    class SaleOrderLine(sillyorm.model.Model):
        _name = "sale_order_line"

        product = sillyorm.fields.String()
        sale_order_id = sillyorm.fields.Many2one("sale_order")

    env.register_model(SaleOrder)
    env.register_model(SaleOrderLine)
    env.init_tables()
    assert_db_columns(
        env.cr, "sale_order", [("id", SqlType.integer()), ("name", SqlType.varchar(255))]
    )
    assert_db_columns(
        env.cr,
        "sale_order_line",
        [
            ("id", SqlType.integer()),
            ("product", SqlType.varchar(255)),
            ("sale_order_id", SqlType.integer()),
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


@with_test_env()
def test_field_many2many(env):
    class Tax(sillyorm.model.Model):
        _name = "tax"

        name = sillyorm.fields.String()

    class Product(sillyorm.model.Model):
        _name = "product"

        tax_ids = sillyorm.fields.Many2many("tax")

    env.register_model(Tax)
    env.register_model(Product)
    assert_db_columns(env.cr, "tax", [("id", SqlType.integer()), ("name", SqlType.varchar(255))])
    assert_db_columns(env.cr, "product", [("id", SqlType.integer())])
    assert_db_columns(
        env.cr,
        "_joint_product_tax_ids_tax",
        [("product_id", SqlType.integer()), ("tax_id", SqlType.integer())],
    )

    tax_1 = env["tax"].create({"name": "tax 1"})
    tax_2 = env["tax"].create({"name": "tax 2"})

    product_1 = env["product"].create({})
    product_2 = env["product"].create({})

    with pytest.raises(SillyORMException) as e_info:
        product_2.tax_ids = (2, None)
    assert str(e_info.value) == "unknown many2many command"

    assert product_1.tax_ids is None
    assert product_2.tax_ids is None

    product_1.tax_ids = (1, tax_1)
    assert repr(product_1.tax_ids) == "tax[1]"
    assert product_2.tax_ids is None

    product_1.tax_ids = (1, tax_2)
    product_2.tax_ids = (1, tax_2)
    assert repr(product_1.tax_ids) == "tax[1, 2]"
    assert repr(product_2.tax_ids) == "tax[2]"

    with pytest.raises(SillyORMException) as e_info:
        product_1.tax_ids = (1, tax_1)
    assert str(e_info.value) == "attempted to insert a record twice into many2many"

    with pytest.raises(SillyORMException) as e_info:
        product_2.tax_ids = (1, tax_2)
    assert str(e_info.value) == "attempted to insert a record twice into many2many"
