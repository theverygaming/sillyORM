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

    def __set__(self, record, value):
        raise Exception("cannot set id")

class String(Field):
    _sql_type = "VARCHAR"

    def __init__(self, name):
        self._name = name

    def __get__(self, record, objtype=None):
        record.cr.execute(f'SELECT "{self._name}" FROM "{record._name}" WHERE "id" IN ({",".join([str(id) for id in record._ids])});')
        result = [x[0] for x in record.cr.fetchall()]
        if len(result) == 1:
            return result[0]
        return result
    
    def __set__(self, record, value):
        if not isinstance(value, str):
            raise Exception("must be string")
        record.cr.execute(f'UPDATE "{record._name}" SET "{self._name}" = \'{value}\' WHERE "id" IN ({",".join([str(id) for id in record._ids])});')
        record.cr.commit()
