import logging
from typing import Any, Iterator, Self
from . import sql, fields
from .sql import SQL
from .environment import Environment
from .exceptions import SillyORMException

_logger = logging.getLogger(__name__)


class Model:
    """
    Each model represents a single table in the database.
    A model can have fields which represent columns in the database table.

    When a model is registered the ORM ensures the table with all required fields is created.
    If any columns/fields exist in the database
    but are not specified in the model **they will be removed in the database**.

    The `_name` attribute specifies the name
    of the database table the model represents
    and the name of the model in the :ref:`environment <environment>`.

    An instance of the model class (or a subclass instance)
    represents a :ref:`recordset <recordsets>`.

    .. warning::
       You should never call the constructor of the model class yourself.
       Get an empty :ref:`recordset <recordsets>` via the
       :ref:`environment <environment>` and interact with the model from there.

    .. testsetup:: models_model

       import tempfile
       import sillyorm
       from sillyorm.dbms import sqlite

       tmpfile = tempfile.NamedTemporaryFile()
       env = sillyorm.Environment(sqlite.SQLiteConnection(tmpfile.name).cursor())

    .. testcode:: models_model

       class ExampleModel(sillyorm.model.Model):
           _name = "example0"
           field = sillyorm.fields.String()

       env.register_model(ExampleModel)
       env.init_tables()

       record = env["example0"].create({"field": "Hello world!"})
       print(record.field)

    .. testoutput:: models_model

       Hello world!

    :ivar env: The environment
    :vartype env: :class:`sillyorm.environment.Environment`

    :param env: The environment
    :type env: :class:`sillyorm.environment.Environment`
    :param ids: list of id's the recordset should have
    :type env: list[int]
    """

    _name = ""
    _extends = ""
    _inherits: list[str] = []
    id = fields.Id()  #: Special :class:`sillyorm.fields.Id` field used as PRIMARY KEY

    def __init__(self, env: Environment, ids: list[int]):
        def get_all_fields() -> dict[str, fields.Field]:
            all_fields = {}
            for cls in self.__class__.__mro__:
                if not issubclass(cls, Model):
                    break
                for attr in vars(cls).values():
                    if not isinstance(attr, fields.Field):
                        continue
                    # fields from classes closer to the
                    # one this function was called on have priority
                    if attr.name not in all_fields:
                        all_fields[attr.name] = attr
            return all_fields

        if not self._name and not self._extends:
            raise SillyORMException("_name or _extends must be set")

        self._ids = ids
        self.env = env
        self._tblmngr = sql.TableManager(self._name)
        self._fields = get_all_fields()

    def __repr__(self) -> str:
        ids = self._ids  # [record.id for record in self]
        return f"{self._name}{ids}"

    def __iter__(self) -> Iterator[Self]:
        for x in self._ids:
            yield self.__class__(self.env, ids=[x])

    def __len__(self) -> int:
        return len(self._ids)

    def __getitem__(self, key: int) -> Self:
        return self.__class__(self.env, ids=[self._ids[key]])

    def _table_init(self) -> None:
        _logger.debug("initializing table for model: '%s'", self._name)
        all_fields = list(self._fields.values())
        _logger.debug("fields for model '%s': %s", self._name, repr(all_fields))
        self._tblmngr.table_init(
            self.env.cr,
            [
                sql.ColumnInfo(field.name, field.sql_type, field.constraints)
                for field in all_fields
                if field.materialize
            ],
            not self.env.update_tables,
        )
        for field in all_fields:
            field.model_post_init(self)

    def ensure_one(self) -> Self:
        """
        Makes sure the recordset contains exactly one record. Raises an exception otherwise

        :raises SillyORMException: If the recordset does not contain exactly one record
        """

        if len(self._ids) != 1:
            raise SillyORMException(f"ensure_one found {len(self._ids)} id's")
        return self

    def read(self, field_names: list[str]) -> list[dict[str, Any]]:
        """
        Reads the specified fields of the recordset.

        :param field_names: The fields to read
        :type field_names: list[str]

        :return:
           The fields read as a list of dictionaries.
        :rtype: list[dict[str, Any]]
        """
        rdata = self._read(field_names)
        for i, data in enumerate(rdata):
            for f, v in data.items():
                val = self._fields[f]._convert_type_get(v)  # pylint: disable=protected-access
                rdata[i][f] = val
        return rdata

    def _read(self, field_names: list[str]) -> list[dict[str, Any]]:
        """
        Reads the specified fields of the recordset. Types returned are directly from the DBMS.

        :param field_names: The fields to read
        :type field_names: list[str]

        :return:
           The fields read as a list of dictionaries.
        :rtype: list[dict[str, Any]]
        """
        if len(self._ids) == 0:
            return []
        order_fix = SQL("")
        # no need to do the order mapping if we are just reading one
        if len(self._ids) > 1:
            order_fix += SQL("ORDER BY CASE {id} ", id=SQL.identifier("id"))
            for i, x in enumerate(self._ids):
                order_fix += SQL("WHEN {id} THEN {n} ", id=x, n=i + 1)
            order_fix += SQL("END")
        return self._tblmngr.read_records(
            self.env.cr,
            field_names,
            SQL(
                "WHERE {id} IN {ids} {order_fix}",
                id=SQL.identifier("id"),
                ids=SQL.set(self._ids),
                order_fix=order_fix,
            ),
        )

    def write(self, vals: dict[str, Any]) -> None:
        """
        Writes the specified fields into
        all records contained in the recordset.

        :param vals:
           The values to write. The keys represent
           the field names and the values the
           values for the fields
        :type vals: dict[str, Any]
        """
        for f, v in vals.items():
            vals[f] = self._fields[f]._convert_type_set(v)  # pylint: disable=protected-access
        self._write(vals)

    def _write(self, vals: dict[str, Any]) -> None:
        """
        Writes the specified fields into
        all records contained in the recordset. Writes directly to the DBMS.

        :param vals:
           The values to write. The keys represent
           the field names and the values the
           values for the fields
        :type vals: dict[str, Any]
        """
        with self.env.managed_transaction():
            self._tblmngr.update_records(
                self.env.cr,
                vals,
                SQL("WHERE {id} IN {ids}", id=SQL.identifier("id"), ids=SQL.set(self._ids)),
            )

    def browse(self, ids: list[int] | int) -> None | Self:
        """
        Returns a recordset for the ids provided.

        .. warning::
           Order of the ids in the recordset returned may
           not be the same as the ids provided as input

        :param ids: The ids or id
        :type vals: list[int] | int

        :return:
           A recordset with the ids provided.
           None if none of the ids could be found
        :rtype: None | Self
        """
        if not isinstance(ids, list):
            ids = [ids]
        res = self.env.cr.execute(
            SQL(
                "SELECT {id} FROM {name} WHERE {id} IN {ids};",
                id=SQL.identifier("id"),
                name=SQL.identifier(self._name),
                ids=SQL.set(ids),
            )
        ).fetchall()
        if len(res) == 0:
            return None
        return self.__class__(self.env, ids=[id[0] for id in res])

    def create(self, vals: dict[str, Any]) -> Self:
        """
        Creates a recordset with the values provided.

        :param vals:
           The values to write into the new recordset.
           The keys represent the field
           names and the values the
           values for the fields
        :type vals: dict[str, Any]

        :return:
           The recordset that was created (containing one record)
        :rtype: Self
        """
        with self.env.managed_transaction():
            top_id = self.env.cr.execute(
                SQL(
                    "SELECT MAX({id}) FROM {table};",
                    id=SQL.identifier("id"),
                    table=SQL.identifier(self._name),
                )
            ).fetchone()[0]
            if top_id is None:
                top_id = 0
            vals["id"] = top_id + 1
            for f, v in vals.items():
                vals[f] = self._fields[f]._convert_type_set(v)  # pylint: disable=protected-access
            self._tblmngr.insert_record(self.env.cr, vals)
            return self.__class__(self.env, ids=[vals["id"]])

    def _domain_transform_types(
        self,
        domain: list[str | tuple[str, str, Any]],
    ) -> list[str | tuple[str, str, Any]]:
        # check types, just in case.. IT SHALL BE ENFORCED,
        # typechecking aint always right esp if u cast...!
        for d in domain:
            if not isinstance(d, (tuple, str)):
                raise SillyORMException("invalid domain")
            if isinstance(d, tuple):
                if not isinstance(d[0], str) or not isinstance(d[1], str) or not len(d) == 3:
                    raise SillyORMException("invalid domain")
        # call the _convert_type_set for each field so we can be sure we are
        # comparing things correctly in the DB!
        for i, d in enumerate(domain):
            if isinstance(d, tuple):
                domain[i] = (
                    d[0],
                    d[1],
                    self._fields[d[0]]._convert_type_set(d[2]),  # pylint: disable=protected-access
                )
        return domain

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def search(
        self,
        domain: list[str | tuple[str, str, Any]],
        order_by: str | None = None,
        order_asc: bool = True,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Self:
        """
        Searches records.

        Search domains are closely tied to the SQL `WHERE` statement.

        .. code-block:: python

           [
               "(",
               ("test2", "=", "test2"),
               "&",
               ("test", "=", "hello world!"),
               ")",
               "|",
               ("test2", "=", "2 Hii!!"),
           ]

        This search domain will result in the following SQL:

        .. code-block:: SQL

           SELECT "id"
           FROM   "test_model"
           WHERE  ( "test2" = 'test2'
                    AND "test" = 'hello world!' )
                   OR "test2" = '2 Hii!!';

        Usage example:

        .. testcode:: models_model

           class ExampleModel(sillyorm.model.Model):
               _name = "example1"
               field = sillyorm.fields.String()

           env.register_model(ExampleModel)
           env.init_tables()

           record1 = env["example1"].create({"field": "test1"})
           record2 = env["example1"].create({"field": "test2"})
           record3 = env["example1"].create({"field": "test3"})
           print(record1.id, record2.id, record3.id)

           print(env["example1"].search([
               ("field", "=", "test1"),
               "|",
               ("field", "!=", "test2"),
           ]))

        .. testoutput:: models_model

           1 2 3
           example1[1, 3]

        :param domain: The search domain.
        :type domain: list[str | tuple[str, str, Any]]
        :param order_by: The column to order by
        :type order_by: str | None
        :param order_asc: Wether the order is ascending or not
        :type order_asc: bool
        :param offset: The row offset to use
        :type offset: int | None
        :param limit: The maximum amount of rows to return
        :type limit: int | None

        :return:
           A recordset with the records found.
           An empty recordset if nothing could be found
        :rtype: Self
        """
        res = self._tblmngr.search_records(
            self.env.cr,
            ["id"],
            self._domain_transform_types(domain),
            order_by,
            order_asc,
            offset,
            limit,
        )
        return self.__class__(self.env, ids=[id[0] for id in res])

    def search_count(
        self,
        domain: list[str | tuple[str, str, Any]],
    ) -> int:
        """
        Counts the total amount of records that match a domain.

        The domain is the same format as for the search function.

        Usage example:

        .. testcode:: models_model

           class ExampleModel(sillyorm.model.Model):
               _name = "example_msc1"
               field = sillyorm.fields.String()

           env.register_model(ExampleModel)
           env.init_tables()

           record1 = env["example_msc1"].create({"field": "test1"})
           record2 = env["example_msc1"].create({"field": "test1"})
           record3 = env["example_msc1"].create({"field": "test2"})

           print(env["example_msc1"].search_count([
               ("field", "=", "test1"),
           ]))

           print(env["example_msc1"].search_count([
               ("field", "=", "test2"),
           ]))

        .. testoutput:: models_model

           2
           1

        :param domain: The search domain.
        :type domain: list[str | tuple[str, str, Any]]

        :return:
           The amount of records that match the provided domain
        :rtype: int
        """
        return self._tblmngr.search_count_records(self.env.cr, self._domain_transform_types(domain))

    def delete(self) -> None:
        """
        Deletes all records in the recordset
        """
        with self.env.managed_transaction():
            self._tblmngr.delete_records(
                self.env.cr,
                SQL("WHERE {id} IN {ids}", id=SQL.identifier("id"), ids=SQL.set(self._ids)),
            )
