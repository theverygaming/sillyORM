.. _basic_concepts:

Basic concepts
==============

.. testsetup:: models_concept

   import tempfile
   import sillyorm
   from sillyorm.dbms import sqlite

   tmpfile = tempfile.NamedTemporaryFile()
   env = sillyorm.Environment(sqlite.SQLiteConnection(tmpfile.name).cursor())

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

   env.register_model(ExampleModel)

When a model is registered the ORM ensures the table with all required fields is created.
If any columns/fields exist in the database but are not specified in the model **they will be removed in the database**.

.. warning::
   You should never call the constructor of the model class yourself.
   Get an empty :ref:`recordset <recordsets>` via the :ref:`environment <environment>` and interact with the model from there.

A model can also be inherited

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example0"

   class ExampleModelCopy(ExampleModel):
       _name = "example0_copy"

   env.register_model(ExampleModelCopy)

This will cause all fields to be copied on the inherited model.
If a field is defined in both the base class and the inherited one the inherited one will be put into the database.
**At the moment it is not possible to remove a field from an inherited model**


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

The database cursor can be accessed from the environment

.. doctest:: models_concept

   # the database cursor can be accessed from the environment
   >>> type(env.cr)
   <class 'sillyorm.dbms.sqlite.SQLiteCursor'>


------
Fields
------

There are various kinds of fields. By default each model has a special :class:`id <sillyorm.fields.Id>` field which is the primary key.

Currently sillyORM supports the following fields:

* :class:`Integer <sillyorm.fields.Integer>` represents an integer
* :class:`String <sillyorm.fields.String>` represents a string
* :class:`Text <sillyorm.fields.Text>` represents a large string
* :class:`Date <sillyorm.fields.Date>` represents a Date (as `datetime.date`)
* :class:`Many2one <sillyorm.fields.Many2one>` represents a many to one relationship
* :class:`One2many <sillyorm.fields.One2many>` represents a one to many relationship (requires a many to one on the other side)


Fields are specified as class attributes on a child of the :class:`Model <sillyorm.model.Model>` class.
The attribute name specifies the column name in the database.

.. testcode:: models_concept

   class ExampleModel(sillyorm.model.Model):
       _name = "example1"

       name = sillyorm.fields.String()

   env.register_model(ExampleModel)


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
   >>> rec_12.name
   ['this is record 1', 'this is record 2']


Recordsets can be iterated over

.. doctest:: models_concept

   >>> rec_12 = env["example1"].browse([1, 2])
   >>> for record in rec_12: record
   example1[1]
   example1[2]

There is a :func:`function <sillyorm.model.Model.ensure_one>` to ensure a recordset contains exactly one record. It will raise an exception if that isn't the case

.. doctest:: models_concept

   >>> rec_1 = env["example1"].browse(1)
   >>> rec_1.ensure_one()
   example1[1]

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

   env.register_model(ExampleModel)
   record = env["example2"].create({"name": "test"})
   record.somefunc()


.. testoutput:: models_concept

   example2[1]
   it: example2[1]
