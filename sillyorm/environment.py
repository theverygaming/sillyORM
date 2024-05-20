from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from . import sql
from .exceptions import SillyORMException

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model

_logger = logging.getLogger(__name__)


class Environment:
    """This class is meant for keeping track of :class:`models <sillyorm.model.Model>`
    registered in it, some settings and the database cursor.

    A model can be registered in the environment using the
    :func:`register_model <sillyorm.environment.Environment.register_model>` function.

    Once registered, models in the environment can be accessed using the index operator.
    When a model is accessed this way, it will return an empty recordset.

    >>> import tempfile
    >>> import sillyorm
    >>> class TestModel(sillyorm.model.Model):
    ...     _name = "testmodel"
    >>> env = sillyorm.Environment(
    ...     sillyorm.dbms.sqlite.SQLiteConnection(
    ...         tempfile.NamedTemporaryFile().name
    ...     ).cursor()
    ... )
    >>> env.register_model(TestModel)
    >>> env["testmodel"]
    testmodel[]

    :ivar cr: The database cursor
    :vartype cr: :class:`sillyorm.sql.Cursor`
    :ivar do_commit: Whether to run commit after each database transaction that requires it
    :vartype do_commit: bool

    :param cursor: The database cursor that will be passed to all models
    :type cursor: :class:`sillyorm.sql.Cursor`
    :param do_commit: Whether to run commit after each database transaction that requires it
    :type do_commit: bool, optional
    """

    def __init__(self, cursor: sql.Cursor, do_commit: bool = True):
        self.cr = cursor
        self.do_commit = do_commit
        self._models: dict[str, type[Model]] = {}

    def register_model(self, model: type[Model]) -> None:
        """
        Registers a model class in the environment

        :param model: The :class:`Model <sillyorm.model.Model>` to register
        :type model: type[:class:`Model <sillyorm.model.Model>`]
        """

        name = model._name  # pylint: disable=protected-access
        if name in self._models:
            raise SillyORMException(f"cannot register model '{name}' twice")
        _logger.info("registering model '%s'", name)
        self._models[name] = model
        model(self, [])._table_init()  # pylint: disable=protected-access

    def __getitem__(self, key: str) -> Model:
        return self._models[key](self, [])
