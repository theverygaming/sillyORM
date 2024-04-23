import re
import pytest
import psycopg2
import sillyORM
from sillyORM import SQLite, postgresql
from sillyORM.sql import SqlType, SqlConstraint


def test_field_base():
    with pytest.raises(Exception) as e_info:
        class SaleOrder(sillyORM.model.Model):
            _name = "sale_order"
            impossible = sillyORM.fields.Field()
    assert str(e_info.value) == "_sql_type must be set"
