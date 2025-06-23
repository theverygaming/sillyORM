from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any, Iterable, Generator
import sqlalchemy
from . import Environment
from .exceptions import SillyORMException

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model

_logger = logging.getLogger(__name__)


class Registry:
    def __init__(self, create_engine_url: str, create_engine_kwargs: dict[str, Any] = {}):
        self.engine = sqlalchemy.create_engine(create_engine_url, **create_engine_kwargs)
        self.metadata = sqlalchemy.MetaData()
        # raw model list, result from register_model calls
        self._raw_models: dict[str, list[type[Model] | str]] = {}
        # finished model list (inheritance applied etc.)
        self._models: dict[str, type[Model]] = {}
        self._environments_given_out: list[Environment] = []

    def reset(self) -> None:
        """
        Reset the registry object, minus the models that have been registered
        """
        self.metadata = sqlalchemy.MetaData()
        self._models = {}
        for env in self._environments_given_out:
            env.close()
            del env

    def register_model(self, model: type[Model]) -> None:
        """
        Registers a model class in the Registry (for later initialization)

        The order in which this function is called on each model matters!
        It determines the exact inheritance!

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
            if extends not in self._raw_models:
                raise SillyORMException(f"cannot extend nonexistant model '{extends}'")
            self._raw_models[extends] += inherits
            self._raw_models[extends].append(model)
            return

        if name in self._raw_models:
            raise SillyORMException(f"cannot register model '{name}' twice")
        _logger.info("registering model '%s'", name)
        self._raw_models[name] = inherits + [model]

    def resolve_tables(self):
        """
        Resolve model inheritance and build the models table in the registry
        """

        self._models = {}

        resolved_model_classes = self._raw_models

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
            for i, v in enumerate(resolved_model_classes[model_name]):
                if not isinstance(v, str):
                    continue
                _build_model_inheritance(v, visited)
                resolved_model_classes[model_name][i] = self._models[v]
            # ensure there are no duplicate classes. Reversed unique because we always want to keep
            # the last occurence (so the class that extended last!)
            resolved_model_classes[model_name] = list(
                reversed(list(_unique(reversed(resolved_model_classes[model_name]))))
            )
            # now we actually build the final model
            _logger.debug(
                "building model '%s' out of %s",
                model_name,
                repr(resolved_model_classes[model_name]),
            )
            self._models[model_name] = type(
                # it's 3am and i want this to work goddamnit, ignore the type stuff
                resolved_model_classes[model_name][0].__name__,  # type: ignore[union-attr]
                tuple(reversed(resolved_model_classes[model_name])),  # type: ignore[arg-type]
                _collect_class_attrs(resolved_model_classes[model_name]),  # type: ignore[arg-type]
            )

        for model_name in resolved_model_classes:
            _build_model_inheritance(model_name)

        for model in self._models.values():
            model._build_sqlalchemy_table(self.metadata)
            _logger.debug(f"table for model '{model._name}': {repr(model._table)}")

    def init_db_tables(self):
        """
        Initializes database tables. Only works on an empty database!
        """
        self.metadata.create_all(self.engine)

    def get_environment(self, autocommit: bool = False) -> Environment:
        """
        Returns a new environment object (will also grab a new connection from the connection pool)

        :param autocommit: Whether to automatically run commit after each database transaction that requires it (and rollback on error)
        :type autocommit: bool, optional

        :return:
           The new Environment object
        :rtype: :class:`environment <sillyorm.environment.Environment>`
        """
        new_env = Environment(self._models, self.engine.connect(), self, autocommit=autocommit)
        self._environments_given_out.append(new_env)
        return new_env
