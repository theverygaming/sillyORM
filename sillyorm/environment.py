from __future__ import annotations
import logging
import contextlib
from typing import TYPE_CHECKING, Generator
import sqlalchemy

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model
    from .registry import Registry

_logger = logging.getLogger(__name__)


class Environment:
    """This class is meant for keeping track of :class:`models <sillyorm.model.Model>`
    registered in it, some settings and the database connection (SQLAlchemy Connection object).

    Once registered, models in the environment can be accessed using the index operator.
    When a model is accessed this way, it will return an empty recordset.

    :ivar connection: The database Connection
    :vartype connection: sqlalchemy.Connection
    :ivar registry: The registry this environment object was created from
    :vartype registry: :class:`sillyorm.registry.Registry`
    :ivar autocommit: Whether to automatically run commit after each database transaction that requires it (and rollback on error)
    :vartype autocommit: bool

    :param models: The database cursor that will be passed to all models
    :param connection: The database connection
    :type connection: sqlalchemy.Connection
    :param registry: The registry this environment object was created from
    :type registry: :class:`sillyorm.registry.Registry`
    :param autocommit: Whether to automatically run commit after each database transaction that requires it (and rollback on error)
    :type autocommit: bool, optional
    """

    def __init__(
        self,
        models: dict[str, type[Model]],
        connection: sqlalchemy.Connection,
        registry: Registry,
        autocommit: bool = False,
    ):
        self._models = models
        self.connection = connection
        self.registry = registry
        self.autocommit = autocommit

    def close(self):
        """
        Close this environment object, close it's connection
        If it has an active transaction that will be rolled back.
        """
        if self.connection is not None:
            if self.connection.get_transaction() is not None:
                self.connection.rollback()
            self.connection = None

    def __del__(self):
        self.close()

    def __getitem__(self, key: str) -> Model:
        return self._models[key](self, [])

    @contextlib.contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """
        Context manager for transactions, this will start a transaction and roll it back on error
        """
        if self.connection.get_transaction() is None:
            self.connection.begin()
        try:
            yield
        except Exception:
            _logger.debug("transaction contextmanager: rollback")
            self.connection.rollback()
            raise
        _logger.debug("transaction contextmanager: commit")
        self.connection.commit()

    @contextlib.contextmanager
    def managed_transaction(self) -> Generator[None, None, None]:
        """
        Context manager for transactions, this is mostly for internal use and will do not do
        _anything_ without autocommit being set!
        """
        if self.autocommit and self.connection.get_transaction() is None:
            self.connection.begin()
        try:
            yield
        except Exception:
            if self.autocommit:
                _logger.debug("managed_transaction contextmanager: rollback")
                self.connection.rollback()
            raise
        if self.autocommit:
            _logger.debug("managed_transaction contextmanager: commit")
            self.connection.commit()
