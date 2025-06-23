import logging
from typing import Any, Iterator, Self, cast
import sqlalchemy
from . import fields
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

    _fields: list[fields.Field] = []
    _table: sqlalchemy.Table = cast(sqlalchemy.Table, None)

    id = fields.Id()  #: Special :class:`sillyorm.fields.Id` field used as PRIMARY KEY

    def __init__(self, env: Environment, ids: list[int]):
        if not self._name and not self._extends:
            raise SillyORMException("_name or _extends must be set")

        self._ids = ids
        self.env = env

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

    @classmethod
    def _build_fields_list(cls) -> None:
        def get_all_fields() -> dict[str, fields.Field]:
            all_fields = {}
            for clsx in cls.__mro__:
                if not issubclass(clsx, Model):
                    break
                for attr in vars(clsx).values():
                    if not isinstance(attr, fields.Field):
                        continue
                    # fields from classes closer to the
                    # one this function was called on have priority
                    if attr.name not in all_fields:
                        all_fields[attr.name] = attr
            return all_fields

        cls._fields = get_all_fields()

    @classmethod
    def _build_sqlalchemy_table(cls, metadata: sqlalchemy.MetaData) -> None:
        cls._build_fields_list()
        all_fields = list(cls._fields.values())

        columns = [
            sqlalchemy.Column(
                field.name,
                field.sql_type,
                *[c for c in field.constraints if not isinstance(c, tuple)],
                **{c[0]: c[1] for c in field.constraints if isinstance(c, tuple)},
            )
            for field in all_fields
            if field.materialize
        ]

        cls._table = sqlalchemy.Table(
            cls._name,
            metadata,
            *columns,
        )

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
        if not self._ids:
            return []

        columns = [self._table.c[field] for field in field_names]
        stmt = sqlalchemy.select(*columns).where(self._table.c.id.in_(self._ids))

        # fix the order
        if len(self._ids) > 1:
            case_ordering = sqlalchemy.case(
                {id_: index for index, id_ in enumerate(self._ids)}, value=self._table.c.id
            )
            stmt = stmt.order_by(case_ordering)

        result = self.env.connection.execute(stmt)
        return [dict(row._mapping) for row in result]

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
        if not self._ids:
            return

        with self.env.managed_transaction():
            stmt = (
                sqlalchemy.update(self._table).where(self._table.c.id.in_(self._ids)).values(**vals)
            )
            self.env.connection.execute(stmt)

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

        stmt = sqlalchemy.select(self._table.c.id).where(self._table.c.id.in_(ids))
        result = self.env.connection.execute(stmt).fetchall()

        if not result:
            return None

        found_ids = [row[0] for row in result]
        return self.__class__(self.env, ids=found_ids)

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
            for f, v in vals.items():
                vals[f] = self._fields[f]._convert_type_set(v)  # pylint: disable=protected-access
            new_id = self.env.connection.execute(
                sqlalchemy.insert(self._table).values(**vals)
            ).inserted_primary_key[0]
            return self.__class__(self.env, ids=[new_id])

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

    def _parse_domain(
        self, domain: list[str | tuple[str, str, Any]]
    ) -> sqlalchemy.sql.elements.ClauseElement:
        def cmp_expr(col, op, val):
            clmn = self._table.c[col]
            match op:
                case "=":
                    return clmn.is_(val) if val is None else (clmn == val)
                case "!=":
                    return clmn.isnot(val) if val is None else (clmn != val)
                case ">":
                    return clmn > val
                case ">=":
                    return clmn >= val
                case "<":
                    return clmn < val
                case "<=":
                    return clmn <= val
                # we only implement ILIKE for now because SQLite doesn't actually support
                # case-sensitive LIKE out of the box without fuckery it seems
                # it appears to be the same with SQLAlchemy??
                case "=ilike":
                    return clmn.ilike(val)
                case "ilike":
                    return clmn.ilike(f"%{val}%")
            raise SillyORMException(f"Unsupported operator {op}")

        def infix2normalpolish(domain):
            left_associative_operators = ["!"]
            operator_precedence = {"!": 3, "&": 2, "|": 1}

            paren_exception = SillyORMException(
                "infix2normalpolish: mismatched parenthesis.. Your domain is broken!"
            )

            # https://en.wikipedia.org/wiki/Shunting_yard_algorithm (adapted for polish notaton as specified in the article)
            output_stack = []
            operator_stack = []
            # rparen and lparen are switched around because we are iterating in reverse!
            # This is what you do if u want normal polish notation instead of reverse polish notation
            for token in reversed(domain):
                if isinstance(token, tuple):
                    output_stack.append(token)
                if token in operator_precedence:
                    o1 = token
                    if operator_stack:
                        o2 = operator_stack[-1]
                        while o2 in operator_precedence and (
                            operator_precedence[o2] > operator_precedence[o1]
                            or (
                                operator_precedence[o2] == operator_precedence[o1]
                                and o1 in left_associative_operators
                            )
                        ):
                            output_stack.append(operator_stack.pop())
                    operator_stack.append(o1)
                if token == ")":
                    operator_stack.append(token)
                if token == "(":
                    while operator_stack and operator_stack[-1] != ")":
                        if not operator_stack:
                            raise paren_exception
                        output_stack.append(operator_stack.pop())
                    if not operator_stack:
                        raise paren_exception
                    operator_stack.pop()
            while operator_stack:
                if operator_stack[-1] == ")":
                    raise paren_exception
                output_stack.append(operator_stack.pop())

            return list(reversed(output_stack))

        def pn_parse(parts_iter):
            try:
                part = next(parts_iter)
            except StopIteration:
                raise SillyORMException(
                    "failed to parse domain, expected at least one further element"
                )
            if part == "&":
                return sqlalchemy.and_(pn_parse(parts_iter), pn_parse(parts_iter))
            elif part == "|":
                return sqlalchemy.or_(pn_parse(parts_iter), pn_parse(parts_iter))
            elif part == "!":
                return sqlalchemy.not_(pn_parse(parts_iter))
            elif isinstance(part, tuple):
                return cmp_expr(*part)
            else:
                raise SillyORMException(f"Invalid domain part: {repr(part)}")

        if not domain:
            return None

        domain_iter = iter(infix2normalpolish(domain))
        result = pn_parse(domain_iter)
        if any(True for _ in domain_iter):
            raise SillyORMException(
                "Domain NPN issue!! It did not get fully parsed.. Are you missing an operator?"
            )
        return result

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

        Search operators:

        *  `=` Equals to
        * `!=` not equal
        * `>` greater than
        * `>=` greater than or equal
        * `<` less than
        * `<=` less than or equal
        * `=ilike` matches against the pattern provided (case-insentitive), `_` in the pattern
          matches any single character and `%` matches any string of zero or more characters
        * `ilike` similar to `=ilike` but will wrap the pattern provided in `%`

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
        if offset is not None and limit is None:
            raise SillyORMException("offset can only be used together with limit")

        stmt = sqlalchemy.select(self._table.c.id)

        filter_expr = self._parse_domain(domain)

        if filter_expr is not None:
            stmt = stmt.where(filter_expr)

        if order_by is not None:
            col = self._table.c[order_by]
            stmt = stmt.order_by(col.asc() if order_asc else col.desc())

        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        result = self.env.connection.execute(stmt).fetchall()
        ids = [row[0] for row in result]

        return self.__class__(self.env, ids=ids)

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
        stmt = sqlalchemy.select(sqlalchemy.func.count()).select_from(self._table)

        filter_expr = self._parse_domain(domain)

        if filter_expr is not None:
            stmt = stmt.where(filter_expr)

        result = self.env.connection.execute(stmt).scalar_one()
        return result

    def delete(self) -> None:
        """
        Deletes all records in the recordset
        """
        if not self._ids:
            return

        with self.env.managed_transaction():
            stmt = sqlalchemy.delete(self._table).where(self._table.c.id.in_(self._ids))
            self.env.connection.execute(stmt)
