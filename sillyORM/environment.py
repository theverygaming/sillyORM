from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from . import sql

if TYPE_CHECKING:
    from .model import Model

_logger = logging.getLogger(__name__)

class Environment():
    def __init__(self, cursor: sql.Cursor):
        self.cr = cursor
        self._models: dict[str, type[Model]] = {}

    def register_model(self, model: type[Model]) -> None:
        name = model._name
        if name in self._models:
            raise RuntimeError(f"cannot register model '{name}' twice")
        _logger.info(f"registering model '{name}'")
        self._models[name] = model
        model(self, [])._table_init()

    def __getitem__(self, key: str) -> Model:
        return self._models[key](self, [])
