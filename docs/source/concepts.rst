.. _basic_concepts:

Basic concepts
==============

.. testsetup:: models_concept

   import tempfile
   import sillyorm

   tmpfile = tempfile.NamedTemporaryFile()
   registry = sillyorm.Registry(f"sqlite:///{tmpfile.name}")

------
Models
------

Each model represents a single table in the database. A model can have fields which represent columns in the database table.

A model is a class that inherits from :class:`sillyorm.model.Model`.
It has a `_name` attribute which specifies the name of the database table
and the name of the model in the :ref:`environment <environment>`.

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example0"

   registry.register_model(ExampleModel)
   registry.resolve_tables()
   registry.init_db_tables()
   env = registry.get_environment()

.. warning::
   You should never call the constructor of the model class yourself.
   Get an empty :ref:`recordset <recordsets>` via the :ref:`environment <environment>` and interact with the model from there.

A model can also be inherited and extended

Standard Python Inheritance:

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example_inheritance"
       field1 = sillyorm.fields.Integer()

   class ExampleModelCopy(ExampleModel):
       _name = "example_inheritance_copy"
       field2 = sillyorm.fields.String()

   registry.register_model(ExampleModel)
   registry.register_model(ExampleModelCopy)
   registry.resolve_tables()
   registry.init_db_tables()
   env = registry.get_environment()
   env["example_inheritance"].create({}).field1
   env["example_inheritance_copy"].create({}).field1
   env["example_inheritance_copy"].create({}).field2

This will cause all fields to be copied on the inherited model.
If a field is defined in both the base class and the inherited one the inherited one will be put into the database.
**At the moment it is not possible to remove a field from an inherited model**

Extension:

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example_extension"
       field1 = sillyorm.fields.Integer()
       field2 = sillyorm.fields.Integer()

   class ExampleModelExtension(sillyorm.model.Model):
       _name = "example_extension"
       _extends = "example_extension"
       # overrides field2 on original model, now field2 is a String
       field2 = sillyorm.fields.String()
       # adds a new field to the original model
       field3 = sillyorm.fields.String()

   registry.register_model(ExampleModel)
   registry.register_model(ExampleModelExtension)
   registry.resolve_tables()
   registry.init_db_tables()
   env = registry.get_environment()
   env["example_extension"].create({}).field1
   env["example_extension"].create({}).field2
   env["example_extension"].create({}).field3

This will add fields/modify fields on the original model.
**At the moment it is not possible to remove a field from an extended model**

Inheritance (via ORM):

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example_orm_inheritance"
       field1 = sillyorm.fields.Integer()

   class ExampleModelCopy(sillyorm.model.Model):
       _name = "example_orm_inheritance_copy"
       _inherits = ["example_orm_inheritance"] # order matters here (later in array has higher priority)
       field2 = sillyorm.fields.String()

   registry.register_model(ExampleModel)
   registry.register_model(ExampleModelCopy)
   registry.resolve_tables()
   registry.init_db_tables()
   env = registry.get_environment()
   env["example_orm_inheritance"].create({}).field1
   env["example_orm_inheritance_copy"].create({}).field1
   env["example_orm_inheritance_copy"].create({}).field2

This will cause all fields to be copied on the inherited model.
If a field is defined in both the base class and the inherited one the inherited one will be put into the database.
**At the moment it is not possible to remove a field from an inherited model**

Inheritance (via ORM) and extension may also be combined:

.. testcode:: models_concept

   class ExampleModelSomefield(sillyorm.model.Model):
       _name = "example_orm_ext_inheritance_somefield"
       somefield = sillyorm.fields.Integer()

   class ExampleModel(sillyorm.model.Model):
       _name = "example_orm_ext_inheritance"
       field1 = sillyorm.fields.Integer()

   class ExampleModelCopy(sillyorm.model.Model):
       _name = "example_orm_ext_inheritance"
       _extends = "example_orm_ext_inheritance"
       _inherits = ["example_orm_ext_inheritance_somefield"] # order matters here (later in array has higher priority)
       field2 = sillyorm.fields.String()

   registry.register_model(ExampleModelSomefield)
   registry.register_model(ExampleModel)
   registry.register_model(ExampleModelCopy)
   registry.resolve_tables()
   registry.init_db_tables()
   env = registry.get_environment()
   env["example_orm_ext_inheritance"].create({}).somefield
   env["example_orm_ext_inheritance"].create({}).field1
   env["example_orm_ext_inheritance"].create({}).field2


.. _registry:

--------
Registry
--------

The :class:`Registry <sillyorm.registry.Registry>` class keeps track of the database connection pool and Model classes.

You can create :ref:`environments <environment>` (kinda like DB cursors) from the registry.

.. doctest:: models_concept

   >>> new_env = registry.get_environment(autocommit=True)
   >>> type(new_env)
   <class 'sillyorm.environment.Environment'>


.. _environment:

-----------
Environment
-----------

The :class:`environment <sillyorm.environment.Environment>` class keeps track of the database cursor and Models registered in the database.

You can get an empty :ref:`recordset <recordsets>` for each model registered in the environment

.. doctest:: models_concept

   >>> env["example0"]
   example0[]

The environment can be accessed from each :ref:`recordset <recordsets>`

.. doctest:: models_concept

   # the environment can be accessed from each recordset
   >>> type(env["example0"].env)
   <class 'sillyorm.environment.Environment'>

The database connection can be accessed from the environment

.. doctest:: models_concept

   # the database connection can be accessed from the environment
   >>> type(env.connection)
   <class 'sqlalchemy.engine.base.Connection'>


------
Fields
------

There are various kinds of fields. By default each model has a special :class:`id <sillyorm.fields.Id>` field which is the primary key.

Currently sillyORM supports the following fields:

* :class:`Integer <sillyorm.fields.Integer>` represents an integer
* :class:`Float <sillyorm.fields.Float>` represents a floating point number
* :class:`String <sillyorm.fields.String>` represents a string
* :class:`Text <sillyorm.fields.Text>` represents a large string
* :class:`Date <sillyorm.fields.Date>` represents a Date (as `datetime.date`)
* :class:`Datetime <sillyorm.fields.Datetime>` represents a Datetime (as `datetime.datetime`)
* :class:`Boolean <sillyorm.fields.Boolean>` represents a Boolean
* :class:`Selection <sillyorm.fields.Selection>` represents a Selection
* :class:`Many2one <sillyorm.fields.Many2one>` represents a many to one relationship
* :class:`One2many <sillyorm.fields.One2many>` represents a one to many relationship (requires a many to one on the other side)

Most fields support None as a value, and are initialized with None by default.

Fields are specified as class attributes on a child of the :class:`Model <sillyorm.model.Model>` class.
The attribute name specifies the column name in the database.

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example1"

       name = sillyorm.fields.String()
       test = sillyorm.fields.String()

   registry.register_model(ExampleModel)
   registry.resolve_tables()
   registry.init_db_tables()
   env = registry.get_environment()


.. _recordsets:

----------
Recordsets
----------

An instance of a model class is a recordset. It may contain none to multiple records.


Recordsets can be empty

.. doctest:: models_concept

   # empty recordset
   >>> env["example1"]
   example1[]


Recordsets can contain single records

.. doctest:: models_concept

   # recordset with one record
   >>> rec_1 = env["example1"].create({"name": "this is record 1"})
   >>> rec_1
   example1[1]
   >>> rec_1.name
   'this is record 1'
   >>> rec_1.id
   1

   # another recordset with one record
   >>> env["example1"].create({"name": "this is record 2"})
   example1[2]

Recordsets can contain multiple records

.. doctest:: models_concept

   # recordset with two records
   >>> rec_12 = env["example1"].browse([1, 2])
   >>> rec_12
   example1[1, 2]
   >>> rec_12.name  # reading of a field is only possible if the recordset contains exactly one record
   Traceback (most recent call last):
   ...
   sillyorm.exceptions.SillyORMException: ensure_one found 2 id's
   >>> rec_12.read(["name"])  # if a recordset with multiple records has to be read use the `read` method
   [{'name': 'this is record 1'}, {'name': 'this is record 2'}]


Recordsets can be iterated over

.. doctest:: models_concept

   >>> rec_12 = env["example1"].browse([1, 2])
   >>> for record in rec_12: record
   example1[1]
   example1[2]

Recordsets can be subscripted

.. doctest:: models_concept

   >>> rec_12 = env["example1"].browse([1, 2])
   >>> rec_12[0]
   example1[1]
   >>> rec_12[1]
   example1[2]

There is a :func:`function <sillyorm.model.Model.ensure_one>` to ensure a recordset contains exactly one record. It will raise an exception if that isn't the case

.. doctest:: models_concept

   >>> rec_1 = env["example1"].browse(1)
   >>> rec_1.ensure_one()
   example1[1]


Fields can have no value

.. doctest:: models_concept

   # recordset with one record
   >>> rec_3 = env["example1"].create({"name": "this is record 3"})
   >>> rec_3
   example1[3]
   >>> repr(rec_3.test)
   'None'
   >>> rec_3.test = "test"
   >>> rec_3.test
   'test'
   >>> rec_3.test = None  # setting a field to None is also possible
   >>> repr(rec_3.test)
   'None'


---------------
Model Functions
---------------

A model can have functions

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example2"

       name = sillyorm.fields.String()

       def somefunc(self):
           print(self)
           for record in self:
               print(f"it: {self}") 

   registry.register_model(ExampleModel)
   registry.resolve_tables()
   registry.init_db_tables()
   env = registry.get_environment()
   record = env["example2"].create({"name": "test"})
   record.somefunc()


.. testoutput:: models_concept

   example2[1]
   it: example2[1]
