"""A lightweight CSV database and SQL-like query engine."""

from .database import Database
from .query import QueryError
from .table import Table

__all__ = ["Database", "QueryError", "Table"]

