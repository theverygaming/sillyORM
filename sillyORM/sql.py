import sqlite3

def _get_conn():
    return sqlite3.connect("test.db")


def sql_table_exists(name):
    cr = _get_conn().cursor()
    res = cr.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}';").fetchone()
    return res == (name,)

def sql_table_create(name, fields):
    if not len(fields):
        raise Exception("cannot create table without columns")
    cr = _get_conn().cursor()
    column_sql = []
    for field in fields:
        sql = f"'{field._name}' {field._sql_type}"
        if field._primary_key:
            sql += " PRIMARY KEY"
        column_sql.append(sql)
    stmt = f'CREATE TABLE "{name}" ({",".join(column_sql)});'
    print(stmt)
    res = cr.execute(stmt)
    if not sql_table_exists(name):
        raise Exception("could not create SQL table")

def sql_get_table_field_values(table, ids, field):
    cr = _get_conn().cursor()
    stmt = f'SELECT "{field}" FROM "{table}" WHERE "id" IN ({",".join([str(id) for id in ids])});'
    print(stmt)
    res = cr.execute(stmt)
    return [x[0] for x in res.fetchall()]
