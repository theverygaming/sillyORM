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
    assert set(env["sale_order"].browse(so_1_id).read(["line_ids"])[0]["line_ids"]) == {
        o1_l1.id,
        o1_l2.id,
        abandoned_so_line1.id,
    }
    assert (
        repr(env["sale_order"].browse(so_2_id).line_ids)
        == f"sale_order_line[{o2_l1.id}, {o2_l2.id}, {o2_l3.id}, {abandoned_so_line2.id}]"
    )
    assert set(env["sale_order"].browse(so_2_id).read(["line_ids"])[0]["line_ids"]) == {
        o2_l1.id,
        o2_l2.id,
        o2_l3.id,
        abandoned_so_line2.id,
    }

    with pytest.raises(NotImplementedError):
        env["sale_order"].browse(so_1_id).line_ids = 1


@with_test_registry()
def test_field_many2one_ondelete(registry):
    class SaleOrderGroup(sillyorm.model.Model):
        _name = "sale_order_group"

        parent_id = sillyorm.fields.Many2one("sale_order_group", ondelete="cascade")
        sale_order_id = sillyorm.fields.Many2one("sale_order", ondelete="cascade")

    class SaleOrder(sillyorm.model.Model):
        _name = "sale_order"

    class SaleOrderLine1(sillyorm.model.Model):
        _name = "sale_order_line"

        sale_order_id = sillyorm.fields.Many2one("sale_order", ondelete="restrict")

    class SaleOrderLine2(sillyorm.model.Model):
        _name = "sale_order_line"

        sale_order_id = sillyorm.fields.Many2one("sale_order", ondelete="set null")

    class SaleOrderLine3(sillyorm.model.Model):
        _name = "sale_order_line"

        sale_order_id = sillyorm.fields.Many2one("sale_order", ondelete="cascade")

    ## restrict
    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderGroup)
    registry.register_model(SaleOrderLine1)
    registry.resolve_tables()
    registry.init_db_tables(automigrate="auto")
    env = registry.get_environment()

    so = env["sale_order"].create({})
    so_group_id = (
        env["sale_order_group"]
        .create(
            {
                "sale_order_id": so.id,
            }
        )
        .id
    )
    so_group2_id = (
        env["sale_order_group"]
        .create(
            {
                "parent_id": so_group_id,
            }
        )
        .id
    )
    sol = env["sale_order_line"].create(
        {
            "sale_order_id": so.id,
        }
    )
    with pytest.raises(sqlalchemy.exc.IntegrityError) as e_info:
        so.delete()
    assert (
        "foreign key constraint" in str(e_info.value).lower()
        and "sale_order" in str(e_info.value).lower()
    )

    ## set null
    registry.reset_full()
    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderGroup)
    registry.register_model(SaleOrderLine2)
    registry.resolve_tables()
    registry.init_db_tables(automigrate="auto")
    env = registry.get_environment()

    so = env["sale_order"].create({})
    so_group_id = (
        env["sale_order_group"]
        .create(
            {
                "sale_order_id": so.id,
            }
        )
        .id
    )
    so_group2_id = (
        env["sale_order_group"]
        .create(
            {
                "parent_id": so_group_id,
            }
        )
        .id
    )
    sol = env["sale_order_line"].create(
        {
            "sale_order_id": so.id,
        }
    )
    so.delete()
    assert sol.sale_order_id is None
    assert env["sale_order_group"].search([("id", "in", [so_group_id, so_group2_id])]).ids == []

    ## cascade
    registry.reset_full()
    registry.register_model(SaleOrder)
    registry.register_model(SaleOrderGroup)
    registry.register_model(SaleOrderLine3)
    registry.resolve_tables()
    registry.init_db_tables(automigrate="auto")
    env = registry.get_environment()

    so = env["sale_order"].create({})
    so_group_id = (
        env["sale_order_group"]
        .create(
            {
                "sale_order_id": so.id,
            }
        )
        .id
    )
    so_group2_id = (
        env["sale_order_group"]
        .create(
            {
                "parent_id": so_group_id,
            }
        )
        .id
    )
    sol_id = (
        env["sale_order_line"]
        .create(
            {
                "sale_order_id": so.id,
            }
        )
        .id
    )
    so.delete()
    assert env["sale_order_line"].search([("id", "=", sol_id)]).ids == []
    assert env["sale_order_group"].search([("id", "in", [so_group_id, so_group2_id])]).ids == []

    # circular reference
    so_group_id = env["sale_order_group"].create({}).id
    so_group2_id = (
        env["sale_order_group"]
        .create(
            {
                "parent_id": so_group_id,
            }
        )
        .id
    )
    so_group3_id = (
        env["sale_order_group"]
        .create(
            {
                "parent_id": so_group2_id,
            }
        )
        .id
    )
    env["sale_order_group"].browse(so_group_id).parent_id = env["sale_order_group"].browse(
        so_group3_id
    )
    env["sale_order_group"].browse(so_group2_id).delete()
    assert (
        env["sale_order_group"]
        .search([("id", "in", [so_group_id, so_group2_id, so_group3_id])])
        .ids
        == []
    )


@with_test_registry()
def test_field_many2many(registry):
    class Tax(sillyorm.model.Model):
        _name = "tax"

        name = sillyorm.fields.String()

    class Product(sillyorm.model.Model):
        _name = "product"

        tax_ids = sillyorm.fields.Many2many("tax")

    registry.register_model(Tax)
    registry.register_model(Product)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        registry,
        "tax",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("name", sqlalchemy.sql.sqltypes.VARCHAR(length=255)),
        ],
    )
    assert_db_columns(
        registry,
        "product",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )
    assert_db_columns(
        registry,
        "join_product_tax_ids_tax",
        [
            ("product_id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("tax_id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )

    tax_1 = env["tax"].create({"name": "tax 1"})
    tax_2 = env["tax"].create({"name": "tax 2"})

    product_1 = env["product"].create({})
    product_2 = env["product"].create({})

    ## LINK
    with pytest.raises(SillyORMException) as e_info:
        product_2.tax_ids = (123, None)
    assert str(e_info.value) == "unknown many2many command"

    assert product_1.tax_ids is None
    assert set(product_1.read(["tax_ids"])[0]["tax_ids"]) == set()
    assert product_2.tax_ids is None
    assert set(product_2.read(["tax_ids"])[0]["tax_ids"]) == set()

    product_1.tax_ids = sillyorm.fields.Many2xCommand.link(tax_1)
    assert repr(product_1.tax_ids) == "tax[1]"
    assert set(product_1.read(["tax_ids"])[0]["tax_ids"]) == {1}
    assert product_2.tax_ids is None
    assert set(product_2.read(["tax_ids"])[0]["tax_ids"]) == set()

    product_1.tax_ids = sillyorm.fields.Many2xCommand.link(tax_2)
    product_2.tax_ids = sillyorm.fields.Many2xCommand.link(tax_2.ids)
    assert repr(product_1.tax_ids) == "tax[1, 2]"
    assert set(product_1.read(["tax_ids"])[0]["tax_ids"]) == {1, 2}
    assert repr(product_2.tax_ids) == "tax[2]"
    assert set(product_2.read(["tax_ids"])[0]["tax_ids"]) == {2}

    # double insert should be ignored
    product_1.tax_ids = sillyorm.fields.Many2xCommand.link(tax_1)
    assert repr(product_1.tax_ids) == "tax[1, 2]"
    assert set(product_1.read(["tax_ids"])[0]["tax_ids"]) == {1, 2}
    product_2.tax_ids = sillyorm.fields.Many2xCommand.link(tax_2)
    assert repr(product_2.tax_ids) == "tax[2]"
    assert set(product_2.read(["tax_ids"])[0]["tax_ids"]) == {2}

    ## UNLINK
    # do nothing
    product_1.tax_ids = sillyorm.fields.Many2xCommand.unlink([])
    assert product_1.tax_ids.ids == [1, 2]
    assert set(product_1.read(["tax_ids"])[0]["tax_ids"]) == {1, 2}
    product_1.tax_ids = sillyorm.fields.Many2xCommand.unlink(tax_1)
    assert product_1.tax_ids.ids == [2]
    assert set(product_1.read(["tax_ids"])[0]["tax_ids"]) == {2}

    product_2.tax_ids = sillyorm.fields.Many2xCommand.unlink(tax_2)
    assert product_2.tax_ids is None
    assert set(product_2.read(["tax_ids"])[0]["tax_ids"]) == set()


@with_test_registry()
def test_field_many2many_2fields(registry):
    class Tax(sillyorm.model.Model):
        _name = "tax"

        product_ids = sillyorm.fields.Many2many("product", "ProductTax", "tax_id", "product_id")

    class Product(sillyorm.model.Model):
        _name = "product"

        tax_ids = sillyorm.fields.Many2many("tax", "ProductTax", "product_id", "tax_id")

    registry.register_model(Tax)
    registry.register_model(Product)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        registry,
        "tax",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )
    assert_db_columns(
        registry,
        "product",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )
    assert_db_columns(
        registry,
        "ProductTax",
        [
            ("product_id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("tax_id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )

    tax_1 = env["tax"].create({})
    tax_2 = env["tax"].create({})

    product_1 = env["product"].create({})
    product_2 = env["product"].create({})

    ## LINK
    assert product_1.tax_ids is None
    assert product_2.tax_ids is None
    assert tax_1.product_ids is None
    assert tax_2.product_ids is None

    product_1.tax_ids = sillyorm.fields.Many2xCommand.link(tax_1)
    assert repr(product_1.tax_ids) == "tax[1]"
    assert repr(tax_1.product_ids) == "product[1]"
    assert product_2.tax_ids is None
    assert tax_2.product_ids is None

    product_1.tax_ids = sillyorm.fields.Many2xCommand.link(tax_2)
    product_2.tax_ids = sillyorm.fields.Many2xCommand.link(tax_2.ids)
    tax_2.product_ids = sillyorm.fields.Many2xCommand.link(product_2.ids)
    assert repr(product_1.tax_ids) == "tax[1, 2]"
    assert repr(tax_1.product_ids) == "product[1]"
    assert repr(tax_2.product_ids) == "product[1, 2]"
    assert repr(product_2.tax_ids) == "tax[2]"

    ## UNLINK
    # do nothing
    tax_1.product_ids = sillyorm.fields.Many2xCommand.unlink([])
    assert product_1.tax_ids.ids == [1, 2]
    assert tax_1.product_ids.ids == [1]
    tax_1.product_ids = sillyorm.fields.Many2xCommand.unlink(product_1)
    assert product_1.tax_ids.ids == [2]
    assert tax_1.product_ids is None

    tax_2.product_ids = sillyorm.fields.Many2xCommand.unlink(product_2)
    assert product_2.tax_ids is None
    assert tax_2.product_ids.ids == [1]


@with_test_registry()
def test_field_many2many_selfref(registry):
    class Tax(sillyorm.model.Model):
        _name = "tax"

        implied_tax_ids = sillyorm.fields.Many2many("tax", "TaxImplied", "tax_id", "implied_tax_id")

    registry.register_model(Tax)
    registry.resolve_tables()
    registry.init_db_tables()
    env = registry.get_environment()
    assert_db_columns(
        registry,
        "tax",
        [
            ("id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )
    assert_db_columns(
        registry,
        "TaxImplied",
        [
            ("tax_id", sqlalchemy.sql.sqltypes.INTEGER()),
            ("implied_tax_id", sqlalchemy.sql.sqltypes.INTEGER()),
        ],
    )

    tax_1 = env["tax"].create({})
    tax_2 = env["tax"].create({})
    tax_3 = env["tax"].create({})

    ## LINK
    assert tax_1.implied_tax_ids is None
    assert tax_2.implied_tax_ids is None
    assert tax_3.implied_tax_ids is None

    tax_1.implied_tax_ids = sillyorm.fields.Many2xCommand.link(tax_3)
    assert repr(tax_1.implied_tax_ids) == "tax[3]"
    assert tax_2.implied_tax_ids is None
    assert tax_3.implied_tax_ids is None

    tax_1.implied_tax_ids = sillyorm.fields.Many2xCommand.link(tax_1)
    tax_2.implied_tax_ids = sillyorm.fields.Many2xCommand.link(tax_1)
    # set because postgres seems to order it differently
    assert set(tax_1.implied_tax_ids.ids) == {1, 3}
    assert repr(tax_2.implied_tax_ids) == "tax[1]"
    assert tax_3.implied_tax_ids is None

    ## UNLINK
    tax_1.implied_tax_ids = sillyorm.fields.Many2xCommand.unlink(tax_1)
    assert tax_1.implied_tax_ids.ids == [3]
