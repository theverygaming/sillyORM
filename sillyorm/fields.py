from __future__ import annotations
from typing import TYPE_CHECKING, Any, cast
import logging
import datetime
from . import sql
from .exceptions import SillyORMException

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model

_logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods


class Field:
    """
    Base descriptor class for :class:`Model <sillyorm.model.Model>` fields

    :cvar sql_type: SQL type of the field
    :vartype sql_type: :class:`sillyorm.sql.SqlType`
    :cvar materialize: Whether the field actually exists as a column in the database table
    :vartype materialize: bool

    :ivar constraints: SQL constraints of the field
    :vartype constraints: list[:class:`sillyorm.sql.SqlConstraint`]
    :ivar name: column name of the field
    :vartype name: str
    :ivar required: If the field must be set (checked via SQL constraints and runtime checks)
    :vartype required: bool
    :ivar unique: If the field's value should be unique in the column (checked via SQL constraints)
    :vartype unique: bool

    :param required: If the field must be set (checked via SQL constraints and runtime checks)
    :type required: bool
    :default required: False
    :param unique: If the field's value should be unique in the column (checked via SQL constraints)
    :type unique: bool
    :default unique: False
    """

    # __must__ be set by all fields
    sql_type: sql.SqlType = cast(sql.SqlType, None)

    # default values
    materialize = True  # if the field should actually exist in tables

    # set automatically
    name: str = cast(str, None)

    def __init__(self, required: bool = False, unique: bool = False) -> None:
        self.constraints: list[sql.SqlConstraint] = []
        self.required = required
        self.unique = unique
        if self.materialize and self.sql_type is None:
            raise SillyORMException("sql_type must be set for all fields that materialize")
        if self.required:
            self.constraints.append(sql.SqlConstraint.not_null())
        if self.unique:
            self.constraints.append(sql.SqlConstraint.unique())

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name}, sql_type={self.sql_type})"

    def model_post_init(self, record: Model) -> None:
        """
        Called by the :class:`Model <sillyorm.model.Model>`
        after the table is initialized

        :param record: The :class:`Model <sillyorm.model.Model>` the field is in
        :type record: :class:`Model <sillyorm.model.Model>`
        """

    def __set_name__(self, record: Model, name: str) -> None:
        self.name = name

    def _convert_type_get(self, value: Any) -> Any:
        return value

    def _convert_type_set(self, value: Any) -> Any:
        if self.required and value is None:
            raise SillyORMException(f"attempted to set required field '{self.name}' to '{value}'")
        return value

    def __get__(self, record: Model, objtype: Any = None) -> Any | list[Any]:
        record.ensure_one()
        sql_result = record._read([self.name])
        result = [self._convert_type_get(res[self.name]) for res in sql_result]
        return result[0]

    def __set__(self, record: Model, value: Any) -> None:
        if value is None:
            record._write({self.name: value})
        record._write({self.name: self._convert_type_set(value)})


class Integer(Field):
    """
    Integer field. Can represent numbers from at least ``-32768`` to ``32767``
    (may be significantly more depending on the dbms used).

    .. testsetup:: models_fields

       import tempfile
       import sillyorm
       from sillyorm.dbms import sqlite

       tmpfile = tempfile.NamedTemporaryFile()
       env = sillyorm.Environment(sqlite.SQLiteConnection(tmpfile.name).cursor())

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example0"
           field = sillyorm.fields.Integer()

       env.register_model(ExampleModel)
       env.init_tables()

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

    sql_type = sql.SqlType.integer()

    def _convert_type_set(self, value: Any) -> Any:
        if not isinstance(value, int) and value is not None:
            raise SillyORMException("Integer value must be int")
        return super()._convert_type_set(value)

    def __set__(self, record: Model, value: int | None) -> None:
        super().__set__(record, value)


class Float(Field):
    """
    Float field. Can represent floating point numbers from at least ``-1.2e-38`` to ``3.4e+38``
    (may be significantly more depending on the dbms used).

    .. testsetup:: models_fields

       import tempfile
       import sillyorm
       from sillyorm.dbms import sqlite

       tmpfile = tempfile.NamedTemporaryFile()
       env = sillyorm.Environment(sqlite.SQLiteConnection(tmpfile.name).cursor())

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_float"
           field = sillyorm.fields.Float()

       env.register_model(ExampleModel)
       env.init_tables()

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

    sql_type = sql.SqlType.float()

    def _convert_type_set(self, value: Any) -> Any:
        if not isinstance(value, float) and value is not None:
            raise SillyORMException("Float value must be float")
        return super()._convert_type_set(value)

    def __set__(self, record: Model, value: float | None) -> None:
        super().__set__(record, value)


class Id(Integer):
    """
    Special ID field used as PRIMARY KEY in model tables. It's value cannot be changed.

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example1"
           # Each model automatically has an ID field

       env.register_model(ExampleModel)
       env.init_tables()

       record = env["example1"].create({})
       record2 = env["example1"].create({})
       print(record.id)
       print(record2.id)

    .. testoutput:: models_fields

       1
       2
    """

    def __init__(self, required: bool = False, unique: bool = False) -> None:
        super().__init__(required=required, unique=unique)
        self.constraints += [sql.SqlConstraint.primary_key()]

    def __get__(self, record: Model, objtype: Any = None) -> int:
        record.ensure_one()
        return record._ids[0]

    def __set__(self, record: Model, value: Any) -> None:
        raise SillyORMException("cannot set id")


class String(Field):
    """
    String field. Represents a string of at most ``length`` characters

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example2"
           field = sillyorm.fields.String()

       env.register_model(ExampleModel)
       env.init_tables()

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
    ) -> None:
        self.sql_type = sql.SqlType.varchar(length)
        super().__init__(required=required, unique=unique)

    def _convert_type_set(self, value: Any) -> Any:
        if not isinstance(value, str) and value is not None:
            raise SillyORMException("String value must be str")
        return super()._convert_type_set(value)

    def __set__(self, record: Model, value: str | None) -> None:
        super().__set__(record, value)


class Text(Field):
    """
    Text field. Represents a large string of text

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_text"
           field = sillyorm.fields.Text()

       env.register_model(ExampleModel)
       env.init_tables()

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

    def __init__(self, required: bool = False, unique: bool = False) -> None:
        self.sql_type = sql.SqlType.text()
        super().__init__(required=required, unique=unique)

    def _convert_type_set(self, value: Any) -> Any:
        if not isinstance(value, str) and value is not None:
            raise SillyORMException("Text value must be str")
        return super()._convert_type_set(value)

    def __set__(self, record: Model, value: str | None) -> None:
        super().__set__(record, value)


class Date(Field):
    """
    Date field. Represents a python date object.

    .. testcode:: models_fields

       import datetime

       class ExampleModel(sillyorm.model.Model):
           _name = "example3"
           field = sillyorm.fields.Date()

       env.register_model(ExampleModel)
       env.init_tables()

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

    sql_type = sql.SqlType.date()

    def _convert_type_get(self, value: Any) -> Any:
        if isinstance(value, str):
            return datetime.date.fromisoformat(value)
        return value

    def _convert_type_set(self, value: Any) -> Any:
        if (
            not isinstance(value, datetime.date) or isinstance(value, datetime.datetime)
        ) and value is not None:
            raise SillyORMException("Date value must be date")
        return super()._convert_type_set(value)

    def __set__(self, record: Model, value: datetime.date | None) -> None:
        super().__set__(record, value)


class Datetime(Field):
    """
    Datetime field. Represents a python datetime object.

    A timezone (or none at all - which means it's naive) must be provided because in the database
    this field does not store any timzeone-related information.
    Mixing timezones would be fatal so this field takes care of that for you.

    :param tzinfo: time zone of the date stored - None means it's a naive datetime object
    :type tzinfo: datetime.tzinfo | None

    .. testcode:: models_fields

       import datetime

       class ExampleModel(sillyorm.model.Model):
           _name = "example_datetime"
           field = sillyorm.fields.Datetime(None)

       env.register_model(ExampleModel)
       env.init_tables()

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

    sql_type = sql.SqlType.timestamp()

    def __init__(
        self, tzinfo: datetime.tzinfo | None, required: bool = False, unique: bool = False
    ) -> None:
        super().__init__(required=required, unique=unique)
        self.tzinfo = tzinfo

    def _convert_type_get(self, value: Any) -> Any:
        if value is not None:
            if isinstance(value, str):
                value = datetime.datetime.fromisoformat(value)
            return value.replace(tzinfo=self.tzinfo)
        return value

    def _convert_type_set(self, value: Any) -> Any:
        if value is not None and not isinstance(value, datetime.datetime):
            raise SillyORMException("Datetime value must be datetime")
        if value is not None:
            if value.tzinfo != self.tzinfo:
                raise SillyORMException(
                    f"Datetime field expected tzinfo '{self.tzinfo}' and got '{value.tzinfo}'"
                )
            value = value.replace(tzinfo=None)
        return super()._convert_type_set(value)

    def __set__(self, record: Model, value: datetime.datetime | None) -> None:
        super().__set__(record, value)


class Boolean(Field):
    """
    Boolean field. Can represent either `True` or `False`.

    .. testsetup:: models_fields

       import tempfile
       import sillyorm
       from sillyorm.dbms import sqlite

       tmpfile = tempfile.NamedTemporaryFile()
       env = sillyorm.Environment(sqlite.SQLiteConnection(tmpfile.name).cursor())

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_bool"
           field = sillyorm.fields.Boolean()

       env.register_model(ExampleModel)
       env.init_tables()

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

    sql_type = sql.SqlType.boolean()

    def _convert_type_get(self, value: Any) -> Any:
        if isinstance(value, int):
            return bool(value)
        return value

    def _convert_type_set(self, value: Any) -> Any:
        if not isinstance(value, bool) and value is not None:
            raise SillyORMException("Boolean value must be bool")
        return super()._convert_type_set(value)

    def __set__(self, record: Model, value: bool | None) -> None:
        super().__set__(record, value)


class Selection(String):
    """
    Selection field.
    Basically just a string field with a little logic around it
    that allows you to choose between multiple different predefined options.

    .. testsetup:: models_fields

       import tempfile
       import sillyorm
       from sillyorm.dbms import sqlite

       tmpfile = tempfile.NamedTemporaryFile()
       env = sillyorm.Environment(sqlite.SQLiteConnection(tmpfile.name).cursor())

    .. testcode:: models_fields

       class ExampleModel(sillyorm.model.Model):
           _name = "example_selection"
           field = sillyorm.fields.Selection(["option1", "option2"])

       env.register_model(ExampleModel)
       env.init_tables()

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
        self, options: list[str], length: int = 255, required: bool = False, unique: bool = False
    ) -> None:
        super().__init__(length, required=required, unique=unique)
        self.options = options

    def _convert_type_set(self, value: Any) -> Any:
        if not (isinstance(value, str) and value in self.options) and value is not None:
            raise SillyORMException("Selection value must be str and in the list of options")
        return super()._convert_type_set(value)


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

       env.register_model(ExampleModel1)
       env.register_model(ExampleModel2)
       env.init_tables()

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

    def __init__(self, foreign_model: str, required: bool = False, unique: bool = False):
        super().__init__(required=required, unique=unique)
        self._foreign_model = foreign_model
        self.constraints += [sql.SqlConstraint.foreign_key(foreign_model, "id")]

    def __get__(self, record: Model, objtype: Any = None) -> None | Model:
        rec = super().__get__(record, objtype)
        if rec is None:
            return None
        return record.env[self._foreign_model].browse(rec)

    def __set__(self, record: Model, value: Model | None) -> None:  # type: ignore[override]
        if value is None:
            super().__set__(record, value)
            return
        value.ensure_one()
        super().__set__(record, value.id)


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

       env.register_model(ExampleModel1)
       env.register_model(ExampleModel2)
       env.init_tables()

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
        self, foreign_model: str, foreign_field: str, required: bool = False, unique: bool = False
    ):
        super().__init__(required=required, unique=unique)
        self._foreign_model = foreign_model
        self._foreign_field = foreign_field

    def __get__(self, record: Model, objtype: Any = None) -> None | Model:
        record.ensure_one()
        return record.env[self._foreign_model].search([(self._foreign_field, "=", record.id)])

    def __set__(self, record: Model, value: Model) -> None:
        raise NotImplementedError()
