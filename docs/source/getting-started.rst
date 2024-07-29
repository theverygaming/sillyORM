Getting Started
===============

sillyORM can interface with two dbms

* SQLite (using python standard library ``sqlite3``)
* PostgreSQL (using ``psycopg2``)

The models etc. you write will be compatible with all of them (unless you write SQL code directly)


-------------------
Basic usage example
-------------------

.. testcode::

   import tempfile  # to create a temporary SQLite database file
   import sillyorm
   # PostgreSQL could be used here instead
   from sillyorm.dbms import sqlite


   # define a model, a model abstracts a table in the database
   class Example(sillyorm.model.Model):
       _name = "example"  # database table name & name in environment

       # fields
       name = sillyorm.fields.String(length=255)
       date = sillyorm.fields.Date()


   # Create the environment
   tmpfile = tempfile.NamedTemporaryFile()
   env = sillyorm.Environment(
       # PostgreSQL could be used here instead
       sqlite.SQLiteConnection(tmpfile.name).cursor()
   )

   # Register the model in the environment
   env.register_model(Example)
   # Create the model table & fields in the database
   env.init_tables()

   # start using the model
   record = env["example"].create({"name": "hello world!"})
   print(f"repr: {repr(record)}")
   print(f"name: {record.name}")
   print(f"date: {record.date}")

.. testoutput::

   repr: example[1]
   name: hello world!
   date: None


-----------------------------------------------
How to integrate sillyORM into your application
-----------------------------------------------

First store the :ref:`environment <environment>` object somewhere where
you can access it from whereever in your application you want to use sillyORM.

Now you can create your models and put them somewhere.
To register them in the environment either call :func:`Environment.register_model <sillyorm.environment.Environment.register_model>` for each model
or to make it a little easier maybe use a `decorator <https://docs.python.org/3/glossary.html#term-decorator>`_.


---------------
Further reading
---------------

Read :ref:`basic_concepts`. It explains far more about models, fields etc. than this guide.
