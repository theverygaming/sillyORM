from __future__ import annotations
from typing import TYPE_CHECKING, Any, cast
import logging
import datetime
import sqlalchemy
from .exceptions import SillyORMException
from .helpers import sanitize_table_name, sanitize_constraint_name

if TYPE_CHECKING:  # pragma: no cover
    from .model import BaseModel

_logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods,too-many-arguments,too-many-positional-arguments


class Field:
    """
    Base descriptor class for :class:`BaseModel <sillyorm.model.BaseModel>` fields

    :cvar sql_type: SQL type of the field
    :vartype sql_type: :class:`sqlalchemy.types.TypeEngine`
    :cvar materialize: Whether the field actually exists as a column in the database table
    :vartype materialize: bool

    :ivar constraints: SQL constraints of the field
    :vartype constraints: list[sqlalchemy.schema.Constraint | tuple[str, Any]]
    :ivar name: column name of the field
    :vartype name: str
    :ivar required: If the field must be set (checked via SQL constraints and runtime checks)
    :vartype required: bool
    :ivar unique: If the field's value should be unique in the column (checked via SQL constraints)
    :vartype unique: bool
    :ivar sql_schema_default: The constant default value for a column
       in the DB Schema. SQL String (e.g. sqlalchemy.text)
    :vartype sql_schema_default: Any
    :ivar default: The constant default value for a column
       inserted during record creation - equivalent to SQLAlchemy Column default=
    :vartype default: Any

    :param required: If the field must be set (checked via SQL constraints and runtime checks)
    :type required: bool
    :default required: False
    :param unique: If the field's value should be unique in the column (checked via SQL constraints)
    :type unique: bool
    :default unique: False
    :param sql_schema_default: The constant default value for a column
       in the DB Schema. SQL String (e.g. sqlalchemy.text)
    :type sql_schema_default: Any
    :default sql_schema_default: None
    :param default: The constant default value for a column
       inserted during record creation - equivalent to SQLAlchemy Column default=
    :type default: Any
    :default default: None
    """

    # __must__ be set by all fields
    sql_type: sqlalchemy.types.TypeEngine[Any] = cast(sqlalchemy.types.TypeEngine[Any], None)

    # default values
    materialize = True  # if the field should actually exist in tables

    # set automatically
    name: str = cast(str, None)

    def __init__(
        self,
        required: bool = False,
        unique: bool = False,
        sql_schema_default: Any = None,
        default: Any = None,
    ) -> None:
        self.required = required
        self.unique = unique
        self.sql_schema_default = sql_schema_default
        self.default = default
        self.constraints: list[sqlalchemy.schema.SchemaItem | tuple[str, Any]] = []

    def _init_field(self, record: type[BaseModel]) -> None:  # pylint: disable=unused-argument
        self.constraints = []
        if self.materialize and self.sql_type is None:
            raise SillyORMException("sql_type must be set for all fields that materialize")
        if self.required:
            self.constraints.append(("nullable", False))
        if self.unique:
            self.constraints.append(("unique", True))
        if self.sql_schema_default is not None:
            self.constraints.append(("server_default", self.sql_schema_default))

    def __set_name__(self, record: BaseModel, name: str) -> None:
        self.name = name

    def _convert_type_get(
        self, record: BaseModel, value: Any  # pylint: disable=unused-argument
    ) -> Any:
        return value

    def _convert_type_set(
        self, record: BaseModel, value: Any  # pylint: disable=unused-argument
    ) -> Any:
        if self.required and value is None:
            raise SillyORMException(f"attempted to set required field '{self.name}' to '{value}'")
        return value

    def __get__(self, record: BaseModel, objtype: Any = None) -> Any:
        record.ensure_one()
        result = record.read([self.name])
        return result[0][self.name]

    def __set__(self, record: BaseModel, value: Any) -> None:
        record.write({self.name: value})

    def _non_materialized_read(self, records: BaseModel) -> list[Any]:
        """
        low-level read method, should be implemented for fields that don't materialize

        returns an array of the values for the recordset
        """
        raise SillyORMException(f"field {self.name} cannot be read")

    def _non_materialized_write(self, records: BaseModel, value: Any) -> None:
        """
        low-level write method, should be implemented for fields that don't materialize
        """
        raise SillyORMException(f"field {self.name} cannot be written")

    def _build_sqlalchemy_table(
        self,
        model_cls: type[BaseModel],  # pylint: disable=unused-argument
        metadata: sqlalchemy.MetaData,  # pylint: disable=unused-argument
    ) -> None:
        return


class Integer(Field):
    """
    Integer field. Can represent numbers from at least ``-32768`` to ``32767``
    (may be significantly more depending on the dbms used).

    .. testsetup:: models_fields

       import tempfile
       import sillyorm

       def reinit_env(m):
           registry = sillyorm.Registry(f"sqlite:///:memory:")
           for x in m:
               registry.register_model(x)
           registry.resolve_tables()
           registry.init_db_tables()
           env = registry.get_environment()
           return env

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example0"
           field = sillyorm.fields.Integer()

       env = reinit_env([ExampleModel])

       record = env["example0"].create({"field": 5})
       print(record.field)
       record.field = -32768
       print(record.field)
       record.field = 32767
       print(record.field)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       5
       -32768
       32767
       None
    """

    sql_type = sqlalchemy.types.Integer()

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if not isinstance(value, int) and value is not None:
            raise SillyORMException("Integer value must be int")
        return super()._convert_type_set(record, value)

    def __set__(self, record: BaseModel, value: int | None) -> None:
        super().__set__(record, value)


class Float(Field):
    """
    Float field. Can represent floating point numbers from at least ``-1.2e-38`` to ``3.4e+38``
    (may be significantly more depending on the dbms used).

    .. testsetup:: models_fields

       import tempfile
       import sillyorm

       tmpfile = tempfile.NamedTemporaryFile()
       registry = sillyorm.Registry(f"sqlite:///{tmpfile.name}")

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_float"
           field = sillyorm.fields.Float()

       env = reinit_env([ExampleModel])

       record = env["example_float"].create({"field": 32768.123321})
       print(record.field)
       record.field = -0.000000000000000000000000000000000000012
       print(record.field)
       record.field = 340000000000000000000000000000000000000.0
       print(record.field)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       32768.123321
       -1.2e-38
       3.4e+38
       None
    """

    sql_type = sqlalchemy.types.Float()

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if not isinstance(value, float) and value is not None:
            raise SillyORMException("Float value must be float")
        return super()._convert_type_set(record, value)

    def __set__(self, record: BaseModel, value: float | None) -> None:
        super().__set__(record, value)


class Id(Integer):
    """
    Special ID field used as PRIMARY KEY in model tables. It's value cannot be changed.

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example1"
           # Each model automatically has an ID field

       env = reinit_env([ExampleModel])

       record = env["example1"].create({})
       record2 = env["example1"].create({})
       print(record.id)
       print(record2.id)

    .. testoutput:: models_fields

       1
       2
    """

    def _init_field(self, record: type[BaseModel]) -> None:
        super()._init_field(record)
        self.constraints += [("primary_key", True)]

    def __get__(self, record: BaseModel, objtype: Any = None) -> int:
        record.ensure_one()
        return record.ids[0]

    def __set__(self, record: BaseModel, value: Any) -> None:
        raise SillyORMException("cannot set id")


class String(Field):
    """
    String field. Represents a string of at most ``length`` characters

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example2"
           field = sillyorm.fields.String()

       env = reinit_env([ExampleModel])

       record = env["example2"].create({"field": "hello"})
       print(record.field)
       record.field += " world!"
       print(record.field)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       hello
       hello world!
       None

    :param length: Maximum string length, defaults to 255
    :type length: int, optional

    """

    def __init__(
        self,
        length: int = 255,
        required: bool = False,
        unique: bool = False,
        sql_schema_default: Any = None,
        default: Any = None,
    ) -> None:
        self.sql_type = sqlalchemy.types.String(length)
        super().__init__(
            required=required, unique=unique, sql_schema_default=sql_schema_default, default=default
        )

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if not isinstance(value, str) and value is not None:
            raise SillyORMException("String value must be str")
        return super()._convert_type_set(record, value)

    def __set__(self, record: BaseModel, value: str | None) -> None:
        super().__set__(record, value)


class Text(Field):
    """
    Text field. Represents a large string of text

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_text"
           field = sillyorm.fields.Text()

       env = reinit_env([ExampleModel])

       record = env["example_text"].create({"field": "hello"})
       print(record.field)
       record.field += " world!"
       print(record.field)

       largestring = "0123456789" * 100000 # 1MB of data
       record.field = largestring
       print(record.field == largestring)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       hello
       hello world!
       True
       None

    """

    def __init__(
        self,
        required: bool = False,
        unique: bool = False,
        sql_schema_default: Any = None,
        default: Any = None,
    ) -> None:
        self.sql_type = sqlalchemy.types.Text()
        super().__init__(
            required=required, unique=unique, sql_schema_default=sql_schema_default, default=default
        )

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if not isinstance(value, str) and value is not None:
            raise SillyORMException("Text value must be str")
        return super()._convert_type_set(record, value)

    def __set__(self, record: BaseModel, value: str | None) -> None:
        super().__set__(record, value)


class Date(Field):
    """
    Date field. Represents a python date object.

    .. testcode:: models_fields

       import datetime

       class ExampleModel(sillyorm.model.Model):
           _name = "example3"
           field = sillyorm.fields.Date()

       env = reinit_env([ExampleModel])

       record = env["example3"].create({"field": datetime.date(1970, 1, 1)})
       print(record.field)
       record.field += datetime.timedelta(days=1)
       print(record.field)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       1970-01-01
       1970-01-02
       None

    """

    sql_type = sqlalchemy.types.Date()

    def _convert_type_get(self, record: BaseModel, value: Any) -> Any:
        return value

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if (
            not isinstance(value, datetime.date) or isinstance(value, datetime.datetime)
        ) and value is not None:
            raise SillyORMException("Date value must be date")
        return super()._convert_type_set(record, value)

    def __set__(self, record: BaseModel, value: datetime.date | None) -> None:
        super().__set__(record, value)


class Datetime(Field):
    """
    Datetime field. Represents a python datetime object.

    A timezone (or the value `None` - which means it's naive) must be
    provided because in the database this field may not store any timzeone-related information.
    Mixing timezones would be fatal so this field takes care of that for you.

    :param tzinfo: time zone of the date stored - None means it's a naive datetime object
    :type tzinfo: datetime.tzinfo | None

    .. testcode:: models_fields

       import datetime

       class ExampleModel(sillyorm.model.Model):
           _name = "example_datetime"
           field = sillyorm.fields.Datetime(None)

       env = reinit_env([ExampleModel])

       record = env["example_datetime"].create({"field": datetime.datetime(1970, 1, 1, 1, 2, 3)})
       print(record.field)
       record.field += datetime.timedelta(days=1, hours=2, minutes=6)
       print(record.field)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       1970-01-01 01:02:03
       1970-01-02 03:08:03
       None

    """

    sql_type = sqlalchemy.types.DateTime()

    def __init__(
        self,
        tzinfo: datetime.tzinfo | None,
        required: bool = False,
        unique: bool = False,
        sql_schema_default: Any = None,
        default: Any = None,
    ) -> None:
        self.tzinfo = tzinfo
        super().__init__(
            required=required, unique=unique, sql_schema_default=sql_schema_default, default=default
        )

    def _convert_type_get(self, record: BaseModel, value: Any) -> Any:
        if value is not None:
            return value.replace(tzinfo=self.tzinfo)
        return value

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if value is not None and not isinstance(value, datetime.datetime):
            raise SillyORMException("Datetime value must be datetime")
        if value is not None:
            if value.tzinfo != self.tzinfo:
                raise SillyORMException(
                    f"Datetime field expected tzinfo '{self.tzinfo}' and got '{value.tzinfo}'"
                )
            value = value.replace(tzinfo=None)
        return super()._convert_type_set(record, value)

    def __set__(self, record: BaseModel, value: datetime.datetime | None) -> None:
        super().__set__(record, value)


class Boolean(Field):
    """
    Boolean field. Can represent either `True` or `False`.

    .. testsetup:: models_fields

       import tempfile
       import sillyorm

       tmpfile = tempfile.NamedTemporaryFile()
       registry = sillyorm.Registry(f"sqlite:///{tmpfile.name}")

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_bool"
           field = sillyorm.fields.Boolean()

       env = reinit_env([ExampleModel])

       record = env["example_bool"].create({"field": True})
       print(record.field)
       record.field = False
       print(record.field)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       True
       False
       None
    """

    sql_type = sqlalchemy.types.Boolean()

    def _convert_type_get(self, record: BaseModel, value: Any) -> Any:
        if isinstance(value, int):
            return bool(value)
        return value

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if not isinstance(value, bool) and value is not None:
            raise SillyORMException("Boolean value must be bool")
        return super()._convert_type_set(record, value)

    def __set__(self, record: BaseModel, value: bool | None) -> None:
        super().__set__(record, value)


class Selection(String):
    """
    Selection field.
    Basically just a string field with a little logic around it
    that allows you to choose between multiple different predefined options.

    .. testsetup:: models_fields

       import tempfile
       import sillyorm

       tmpfile = tempfile.NamedTemporaryFile()
       registry = sillyorm.Registry(f"sqlite:///{tmpfile.name}")

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_selection"
           field = sillyorm.fields.Selection(["option1", "option2"])

       env = reinit_env([ExampleModel])

       record = env["example_selection"].create({"field": "option1"})
       print(record.field)
       record.field = "option2"
       print(record.field)
       record.field = None
       print(record.field)

    .. testoutput:: models_fields

       option1
       option2
       None

    :param options: List of possible selection options
    :type options: list[str]
    :param length: Maximum selection length, defaults to 255
    :type length: int, optional

    """

    def __init__(
        self,
        options: list[str],
        length: int = 255,
        required: bool = False,
        unique: bool = False,
        sql_schema_default: Any = None,
        default: Any = None,
    ) -> None:
        self.options = options
        super().__init__(
            length,
            required=required,
            unique=unique,
            sql_schema_default=sql_schema_default,
            default=default,
        )

    def _convert_type_set(self, record: BaseModel, value: Any) -> Any:
        if not (isinstance(value, str) and value in self.options) and value is not None:
            raise SillyORMException("Selection value must be str and in the list of options")
        return super()._convert_type_set(record, value)


class Many2one(Integer):
    """
    Many to one relational field. Represents a single record of another model.

    When read this field returns a recordset.
    When written it expects an integer (the ID of a foreign record).

    .. testcode:: models_fields

       class ExampleModel1(sillyorm.model.Model):
           _name = "example4"
           field = sillyorm.fields.String()

       class ExampleModel2(sillyorm.model.Model):
           _name = "example5"
           many2one_field = sillyorm.fields.Many2one("example4")

       env = reinit_env([ExampleModel1, ExampleModel2])

       other_record = env["example4"].create({"field": "Hello world!"})
       record = env["example5"].create({"many2one_field": other_record.id})

       print(other_record.field)
       print(record.many2one_field)
       print(record.many2one_field.field)
       record.many2one_field.field = "test"
       print(other_record.field)
       record.many2one_field = None
       print(record.many2one_field)

    .. testoutput:: models_fields

       Hello world!
       example4[1]
       Hello world!
       test
       None

    :param foreign_model: Foreign model name
    :type foreign_model: str

    """

    def __init__(
        self,
        foreign_model: str,
        required: bool = False,
        unique: bool = False,
        sql_schema_default: Any = None,
        default: Any = None,
    ):
        super().__init__(
            required=required, unique=unique, sql_schema_default=sql_schema_default, default=default
        )
        self._foreign_model = foreign_model

    def _init_field(self, record: type[BaseModel]) -> None:
        super()._init_field(record)
        self.constraints += [
            sqlalchemy.ForeignKey(
                f"{sanitize_table_name(self._foreign_model)}.id",
                name=sanitize_constraint_name(
                    f"{sanitize_table_name(record._name)}_{sanitize_table_name(self.name)}"  # pylint: disable=protected-access
                    + f"_{sanitize_table_name(self._foreign_model)}_fk"
                ),
            )
        ]

    def __get__(self, record: BaseModel, objtype: Any = None) -> None | BaseModel:
        rec = super().__get__(record, objtype)
        if rec is None:
            return None
        return record.env[self._foreign_model].browse(rec)

    def __set__(self, record: BaseModel, value: BaseModel | None) -> None:  # type: ignore[override]
        if value is None:
            super().__set__(record, value)
            return
        value.ensure_one()
        super().__set__(record, value.id)


class Many2xCommand:
    """
    Commands for One2many and Many2many fields
    """

    LINK = 1
    UNLINK = 2

    @classmethod
    def link(cls, foreign: BaseModel | list[int]) -> tuple[int, list[int]]:
        """
        LINK command

        links existing records to the relation
        """
        if isinstance(foreign, list):
            return (cls.LINK, foreign)
        return (cls.LINK, foreign.ids)

    @classmethod
    def unlink(cls, foreign: BaseModel | list[int]) -> tuple[int, list[int]]:
        """
        UNLINK command

        removes links of records from the relation
        """
        if isinstance(foreign, list):
            return (cls.UNLINK, foreign)
        return (cls.UNLINK, foreign.ids)


class One2many(Field):
    """
    One to many relational field.
    It's the inverse of a :class:`Many2one <sillyorm.fields.Many2one>` field.
    Represents multiple records of another model.
    This field does not exist in the database table.

    When read this field returns a recordset.
    It cannot be written.

    .. testcode:: models_fields

       class ExampleModel1(sillyorm.model.Model):
           _name = "example6"
           field = sillyorm.fields.String()
           one2many_field = sillyorm.fields.One2many("example7", "many2one_field")

       class ExampleModel2(sillyorm.model.Model):
           _name = "example7"
           many2one_field = sillyorm.fields.Many2one("example6")

       env = reinit_env([ExampleModel1, ExampleModel2])

       other_record = env["example6"].create({})
       record = env["example7"].create({"many2one_field": other_record.id})
       record2 = env["example7"].create({"many2one_field": other_record.id})

       print(record.many2one_field)
       print(record2.many2one_field)
       print(other_record.one2many_field)

    .. testoutput:: models_fields

       example6[1]
       example6[1]
       example7[1, 2]

    :param foreign_model: Foreign model name
    :type foreign_model: str
    :param foreign_field: Foreign :class:`Many2one <sillyorm.fields.Many2one>` field name
    :type foreign_field: str

    """

    materialize = False

    def __init__(
        self,
        foreign_model: str,
        foreign_field: str,
        required: bool = False,
        unique: bool = False,
        sql_schema_default: Any = None,
        default: Any = None,
    ):
        super().__init__(
            required=required, unique=unique, sql_schema_default=sql_schema_default, default=default
        )
        self._foreign_model = foreign_model
        self._foreign_field = foreign_field

    def _non_materialized_read(self, records: BaseModel) -> list[Any]:
        return [
            record.env[self._foreign_model].search([(self._foreign_field, "=", record.id)]).ids
            for record in records
        ]

    def __get__(self, record: BaseModel, objtype: Any = None) -> None | BaseModel:
        val = super().__get__(record, objtype)
        return record.env[self._foreign_model].browse(val)

    def __set__(self, record: BaseModel, value: BaseModel) -> None:
        raise NotImplementedError()


class Many2many(Field):
    """
    Many to many relational field.

    .. warning::
       This field's implementation is currently incomplete

    """

    materialize = False

    def __init__(
        self,
        foreign_model: str,
        join_table_name: str = "",
        join_table_self_name: str = "",
        join_table_foreign_name: str = "",
    ):
        super().__init__()
        self._foreign_model = foreign_model
        self._join_table_name = join_table_name
        self._join_table_self_name = join_table_self_name
        self._join_table_foreign_name = join_table_foreign_name
        self._table = cast(sqlalchemy.Table, None)

    def _build_sqlalchemy_table(
        self, model_cls: type[BaseModel], metadata: sqlalchemy.MetaData
    ) -> None:
        if not self._join_table_name:
            # pylint: disable=protected-access
            self._join_table_name = (
                f"join_{sanitize_table_name(model_cls._name)}"
                + f"_{self.name}"
                + f"_{sanitize_table_name(self._foreign_model)}"
            )
        if not self._join_table_self_name:
            self._join_table_self_name = (
                f"{sanitize_table_name(model_cls._name)}_id"  # pylint: disable=protected-access
            )
        if not self._join_table_foreign_name:
            self._join_table_foreign_name = f"{sanitize_table_name(self._foreign_model)}_id"

        _logger.debug(
            "initializing many2many join table: '%s.%s' -> '%s' named '%s'",
            model_cls._name,  # pylint: disable=protected-access
            self.name,
            self._foreign_model,
            self._join_table_name,
        )
        columns = [
            sqlalchemy.Column(
                self._join_table_self_name,
                sqlalchemy.types.Integer(),
                sqlalchemy.ForeignKey(
                    f"{sanitize_table_name(model_cls._name)}.id",  # pylint: disable=protected-access
                    name=sanitize_constraint_name(
                        f"{sanitize_table_name(self._join_table_name)}"
                        + f"_{sanitize_table_name(self._join_table_self_name)}"
                        + f"_{sanitize_table_name(model_cls._name)}_fk"  # pylint: disable=protected-access
                    ),
                ),
            ),
            sqlalchemy.Column(
                self._join_table_foreign_name,
                sqlalchemy.types.Integer(),
                sqlalchemy.ForeignKey(
                    f"{sanitize_table_name(self._foreign_model)}.id",
                    name=sanitize_constraint_name(
                        f"{sanitize_table_name(self._join_table_name)}_"
                        + f"{sanitize_table_name(self._join_table_foreign_name)}"
                        + f"_{sanitize_table_name(self._foreign_model)}_fk"
                    ),
                ),
            ),
        ]
        # if a table already exists check if it has the correct columns
        table_name_sanitized = sanitize_table_name(self._join_table_name)
        if table_name_sanitized in metadata.tables:
            if set(c.name for c in columns) != set(
                metadata.tables[table_name_sanitized].columns.keys()
            ):
                raise SillyORMException("many2many: column mismatch")
        self._table = sqlalchemy.Table(
            table_name_sanitized,
            metadata,
            *columns,
            sqlalchemy.UniqueConstraint(
                self._join_table_self_name,
                self._join_table_foreign_name,
                name=sanitize_constraint_name(
                    f"{table_name_sanitized}_{self._join_table_self_name}"
                    + f"_{self._join_table_foreign_name}_unique"
                ),
            ),
            keep_existing=True,
        )

    def _non_materialized_read(self, records: BaseModel) -> list[Any]:
        def _read_ids(record: BaseModel) -> list[int]:
            stmt = sqlalchemy.select(self._table.c[self._join_table_foreign_name])
            stmt = stmt.where(self._table.c[self._join_table_self_name] == record.id)
            result = record.env.connection.execute(stmt).fetchall()
            ids = [row[0] for row in result]
            return ids

        return [_read_ids(record) for record in records]

    def __get__(self, record: BaseModel, objtype: Any = None) -> None | BaseModel:
        val = super().__get__(record, objtype)
        if len(val) == 0:
            return None
        return record.env[self._foreign_model].browse(val)

    def __set__(self, record: BaseModel, command: tuple[int, *tuple[Any, ...]] | list[Any]) -> None:
        record.ensure_one()
        cmd: int = command[0]
        match cmd:
            case Many2xCommand.LINK:
                if len(command) != 2:
                    raise SillyORMException("invalid command tuple")
                ids_f: list[int] = command[1]
                for id_f in ids_f:
                    count = record.env.connection.execute(
                        # pylint: disable=not-callable # https://github.com/sqlalchemy/sqlalchemy/discussions/9202
                        sqlalchemy.select(sqlalchemy.func.count())
                        .select_from(self._table)
                        .where(
                            sqlalchemy.and_(
                                self._table.c[self._join_table_self_name] == record.id,
                                self._table.c[self._join_table_foreign_name] == id_f,
                            )
                        )
                    ).scalar_one()
                    if count > 0:
                        # linking an ID twice will be ignored
                        continue
                    with record.env.managed_transaction():
                        record.env.connection.execute(
                            sqlalchemy.insert(self._table).values(
                                {
                                    self._join_table_self_name: record.id,
                                    self._join_table_foreign_name: id_f,
                                }
                            )
                        )
            case Many2xCommand.UNLINK:
                if len(command) != 2:
                    raise SillyORMException("invalid command tuple")
                ids_f: list[int] = command[1]  # type: ignore
                if ids_f:
                    with record.env.managed_transaction():
                        record.env.connection.execute(
                            self._table.delete().where(
                                sqlalchemy.and_(
                                    self._table.c[self._join_table_self_name] == record.id,
                                    self._table.c[self._join_table_foreign_name].in_(ids_f),
                                )
                            )
                        )
            case _:
                raise SillyORMException("unknown many2many command")
