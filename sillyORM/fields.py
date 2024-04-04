from . import sql

class Field():
    # __must__ be set by all fields
    _name = None
    _sql_type = None

    # default values
    _primary_key = False


class Id(Field):
    _name = "id"
    _sql_type = "INTEGER"

    _primary_key = True

    def __get__(self, record, objtype=None):
        record.ensure_one()
        return record._ids[0]


class String(Field):
    _sql_type = "VARCHAR"

    def __init__(self, name):
        self._name = name

    def __get__(self, record, objtype=None):
        result = sql.sql_get_table_field_values(record._name, record._ids, self._name)
        if len(result) == 1:
            return result[0]
        return result
