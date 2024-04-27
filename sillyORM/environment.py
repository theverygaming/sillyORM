from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from . import sql
from .exceptions import SillyORMException

if TYPE_CHECKING:  # pragma: no cover
    from .model import Model

_logger = logging.getLogger(__name__)

class Environment():
    def __init__(self, cursor: sql.Cursor, do_commit: bool = True):
        self.cr = cursor
        self.do_commit = do_commit
        self._models: dict[str, type[Model]] = {}

    def register_model(self, model: type[Model]) -> None:
        name = model._name
        if name in self._models:
            raise SillyORMException(f"cannot register model '{name}' twice")
        _logger.info(f"registering model '{name}'")
        self._models[name] = model
        model(self, [])._table_init()

    def __getitem__(self, key: str) -> Model:
        return self._models[key](self, [])
