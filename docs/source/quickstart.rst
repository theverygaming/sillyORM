Quickstart
==========

======
Models
======

.. testsetup:: models

   import tempfile
   import sillyorm
   from sillyorm.dbms import SQLite

.. testcleanup:: models

   tmpfile = tempfile.NamedTemporaryFile()
   env = sillyorm.Environment(SQLite.SQLiteConnection(tmpfile.name).cursor())
   env.register_model(ExampleModel)  # FIXME: this probably doesn't actually work


------
Basics
------

Each model represents a single table in the database. A model can have fields which represent columns in the database table.

A model is a class that inherits from :class:`sillyorm.model.Model`.
It has a `_name` attribute which specifies the name of the database table
and the name of the model in the :class:`environment <sillyorm.environment.Environment>`.

..
   TODO: reference environment section

.. testcode:: models

   class ExampleModel(sillyorm.model.Model):
       _name = "example"

When a model is registered the ORM ensures the table with all required fields is created.
If any columns/fields exist in the database but are not specified in the model **they will be removed in the database**.


------
Fields
------

There are various kinds of fields. By default each model has a special :class:`id <sillyorm.fields.Id>` field which is the primary key.

Currently sillyORM supports the following fields:

* :class:`Integer <sillyorm.fields.Integer>` represents an integer
* :class:`String <sillyorm.fields.String>` represents a string
* :class:`Date <sillyorm.fields.Date>` represents a Date (as `datetime.date`)
* :class:`Many2one <sillyorm.fields.Many2one>` represents a many to one relationship
* :class:`One2many <sillyorm.fields.One2many>` represents a one to many relationship (requires a many to one on the other side)
* :class:`Many2many <sillyorm.fields.Many2many>` represents a many to many relationship


Fields are specified as class attributes on a child of the :class:`Model <sillyorm.model.Model>` class.
The attribute name specifies the column name in the database.

.. testcode:: models

   class ExampleModel(sillyorm.model.Model):
       _name = "example"

       name = sillyorm.fields.String()

..
   TODO: describe recordsets

..
   TODO: describe functions
