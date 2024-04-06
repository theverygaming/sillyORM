from . import sql
from .sql import SQL

class Field():

    # __must__ be set by all fields
    _sql_type = None

    # set by models
    _name = None

    # default values
    _primary_key = False

    def __set__(self, record, value):
        record.cr.execute(SQL(
            "UPDATE {table} SET {field} = {value} WHERE {id} IN {ids};",
            table=SQL.identifier(record._name),
            field=SQL.identifier(self._name),
            value=SQL.escape(value),
            id=SQL.identifier("id"),
            ids=SQL.set(record._ids),
        ))
        record.cr.commit()

class Id(Field):
    _sql_type = sql.SqlType.INTEGER

    _primary_key = True

    def __get__(self, record, objtype=None):
        record.ensure_one()
        return record._ids[0]

    def __set__(self, record, value):
        raise Exception("cannot set id")

class String(Field):
    _sql_type = sql.SqlType.VARCHAR

    def __get__(self, record, objtype=None):
        record.cr.execute(SQL(
            "SELECT {field} FROM {table} WHERE {id} IN {ids};",
            field=SQL.identifier(self._name),
            table=SQL.identifier(record._name),
            id=SQL.identifier("id"),
            ids=SQL.set(record._ids),
        ))
        result = [x[0] for x in record.cr.fetchall()]
        if len(result) == 1:
            return result[0]
        return result
    
    def __set__(self, record, value):
        if not isinstance(value, str):
            raise Exception("must be string")
        super().__set__(record, value)
