from __future__ import annotations
import logging
import contextlib
from typing import TYPE_CHECKING, Any, Iterable, Generator
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
    >>> env.init_tables()
    >>> env["testmodel"]
    testmodel[]

    :ivar cr: The database cursor
    :vartype cr: :class:`sillyorm.sql.Cursor`
    :ivar do_commit: Whether to run commit after each database transaction that requires it
    :vartype do_commit: bool
    :ivar update_tables: Whether to update database tables.
    :vartype update_tables: bool

    :param cursor: The database cursor that will be passed to all models
    :type cursor: :class:`sillyorm.sql.Cursor`
    :param do_commit: Whether to run commit after each database transaction that requires it
    :type do_commit: bool, optional
    :param update_tables: Whether to automagically update database tables.
        This can be dangerous in some cases, e.g. when a field is renamed or
        field parameters are changed, **all data in the field may be lost**!

        When this is `False` and the tables don't match an error will be thrown upon calling
        :func:`Environment.init_tables <sillyorm.environment.Environment.init_tables>`
    """

    def __init__(self, cursor: sql.Cursor, do_commit: bool = True, update_tables: bool = True):
        self.cr = cursor
        self.do_commit = do_commit
        self.update_tables = update_tables
        # used during initialization
        self._lmodels: dict[str, list[type[Model] | str]] = {}
        # used during operation
        self._models: dict[str, type[Model]] = {}

    def register_model(self, model: type[Model]) -> None:
        """
        Registers a model class in the environment

        :param model: The :class:`Model <sillyorm.model.Model>` to register
        :type model: type[:class:`Model <sillyorm.model.Model>`]
        """

        name = model._name  # pylint: disable=protected-access
        extends = model._extends  # pylint: disable=protected-access
        inherits = model._inherits  # pylint: disable=protected-access

        # sanity checks
        if not name:
            raise SillyORMException(
                "cannot register a model without _name set (in case of extension you also need to"
                " set _name, for inheritance reasons)"
            )
        if extends and name != extends:
            raise SillyORMException("_name must be equal to _extends")

        if extends:
            if extends not in self._lmodels:
                raise SillyORMException(f"cannot extend nonexistant model '{extends}'")
            self._lmodels[extends] += inherits
            self._lmodels[extends].append(model)
            return

        if name in self._lmodels:
            raise SillyORMException(f"cannot register model '{name}' twice")
        _logger.info("registering model '%s'", name)
        self._lmodels[name] = inherits + [model]

    def init_tables(self) -> None:
        """
        Initializes database tables of all models registered
        in the environment and takes care of model inheritance
        """

        def _collect_class_attrs(classes: list[type[Model]]) -> dict[str, Any]:
            attrs = {}
            for cls in classes:
                for k, v in vars(cls).items():
                    attrs[k] = v
            return attrs

        def _unique(it: Iterable[Any]) -> Generator[Any, None, None]:
            visited = set()
            for x in it:
                if x in visited:
                    continue
                visited.add(x)
                yield x

        def _build_model_inheritance(model_name: str, visited: set[str] | None = None) -> None:
            # already done for this model?
            if model_name in self._models:
                return

            # Circular dependency detection
            if visited is None:
                visited = set()
            if model_name in visited:
                raise SillyORMException(
                    f"Circular dependency in model inheritance: '{model_name}' - involved models:"
                    f" '{', '.join(sorted(visited))}'"
                )
            visited.add(model_name)

            # replace all strings with actual model class types and take care of
            # inheritance (we need to make sure things we inherit from are fully built
            # first, we do NOT want to inherit from a incomplete model, that would be very bad)
            for i, v in enumerate(self._lmodels[model_name]):
                if not isinstance(v, str):
                    continue
                _build_model_inheritance(v, visited)
                self._lmodels[model_name][i] = self._models[v]
            # ensure there are no duplicate classes. Reversed unique because we always want to keep
            # the last occurence (so the class that extended last!)
            self._lmodels[model_name] = list(
                reversed(list(_unique(reversed(self._lmodels[model_name]))))
            )
            # now we actually build the final model
            _logger.debug(
                "building model '%s' out of %s",
                model_name,
                repr(self._lmodels[model_name]),
            )
            self._models[model_name] = type(
                # it's 3am and i want this to work goddamnit, ignore the type stuff
                self._lmodels[model_name][0].__name__,  # type: ignore[union-attr]
                tuple(reversed(self._lmodels[model_name])),  # type: ignore[arg-type]
                _collect_class_attrs(self._lmodels[model_name]),  # type: ignore[arg-type]
            )

        for model_name in self._lmodels:
            _build_model_inheritance(model_name)

        for model in self._models.values():
            model(self, [])._table_init()  # pylint: disable=protected-access

        for model_name in self._models:
            if self[model_name]._name != model_name:  # pylint: disable=protected-access
                raise SillyORMException(
                    "something went very wrong during environment initialization"
                    f" env['{model_name}']._name = {self[model_name]._name}"  # pylint: disable=protected-access
                )

    def __getitem__(self, key: str) -> Model:
        return self._models[key](self, [])

    @contextlib.contextmanager
    def managed_transaction(self) -> Generator[None, None, None]:
        """
        Context manager for transactions, only actually does anything
        when do_commit is set on the environment object
        """
        try:
            yield
        except Exception:
            if self.do_commit:
                self.cr.rollback()
            raise
        if self.do_commit:
            self.cr.commit()
