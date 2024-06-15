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
    id = fields.Id()  #: Special :class:`sillyorm.fields.Id` field used as PRIMARY KEY

    def __init__(self, env: Environment, ids: list[int]):
        if not self._name:
            raise SillyORMException("_name must be set")

        self._ids = ids
        self.env = env
        self._tblmngr = sql.TableManager(self._name)

    def __repr__(self) -> str:
        ids = self._ids  # [record.id for record in self]
        return f"{self._name}{ids}"

    def __iter__(self) -> Iterator[Self]:
        for x in self._ids:
            yield self.__class__(self.env, ids=[x])

    def __len__(self) -> int:
        return len(self._ids)

    def _table_init(self) -> None:
        def get_all_fields() -> list[fields.Field]:
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
            return list(all_fields.values())

        _logger.debug("initializing table for model: '%s'", self._name)
        all_fields = get_all_fields()
        _logger.debug("fields for model '%s': %s", self._name, repr(all_fields))
        # TODO: a way to disable updating tables manually so accidents don't happen? # pylint: disable=fixme
        self._tblmngr.table_init(
            self.env.cr,
            [
                sql.ColumnInfo(field.name, field.sql_type, field.constraints)
                for field in all_fields
                if field.materialize
            ],
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
        return self._tblmngr.read_records(
            self.env.cr,
            field_names,
            SQL("WHERE {id} IN {ids}", id=SQL.identifier("id"), ids=SQL.set(self._ids)),
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
        self._tblmngr.update_records(
            self.env.cr,
            vals,
            SQL("WHERE {id} IN {ids}", id=SQL.identifier("id"), ids=SQL.set(self._ids)),
        )
        if self.env.do_commit:
            self.env.cr.commit()

    def browse(self, ids: list[int] | int) -> None | Self:
        """
        Returns a recordset for the ids provided.

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
        self._tblmngr.insert_record(self.env.cr, vals)
        if self.env.do_commit:
            self.env.cr.commit()
        return self.__class__(self.env, ids=[vals["id"]])

    def search(self, domain: list[str | tuple[str, str, Any]]) -> Self:
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

        :return:
           A recordset with the records found.
           An empty recordset if nothing could be found
        :rtype: Self
        """
        res = self._tblmngr.search_records(self.env.cr, ["id"], domain)
        return self.__class__(self.env, ids=[id[0] for id in res])

    def delete(self) -> None:
        """
        Deletes all records in the recordset
        """
        self._tblmngr.delete_records(
            self.env.cr,
            SQL("WHERE {id} IN {ids}", id=SQL.identifier("id"), ids=SQL.set(self._ids)),
        )
        if self.env.do_commit:
            self.env.cr.commit()
