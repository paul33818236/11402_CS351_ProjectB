"""Public database API."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence

from .query import QueryEngine
from .table import Table


class Database:
    """A collection of in-memory CSV tables."""

    def __init__(self) -> None:
        self.tables = {}
        self.query_engine = QueryEngine(self)

    def load_table(self, name: str, path: str, encoding: str = "utf-8-sig") -> Table:
        table = Table.from_csv(name, path, encoding)
        self.tables[name.lower()] = table
        return table

    def create_table(
        self,
        name: str,
        columns: Sequence[str],
        rows: Optional[Iterable[Mapping[str, Any]]] = None,
    ) -> Table:
        table = Table(name, columns, rows)
        self.tables[name.lower()] = table
        return table

    def get_table(self, name: str) -> Table:
        try:
            return self.tables[name.lower()]
        except KeyError:
            raise KeyError(f"Unknown table '{name}'")

    def drop_table(self, name: str) -> None:
        try:
            del self.tables[name.lower()]
        except KeyError:
            raise KeyError(f"Unknown table '{name}'")

    def create_index(self, table: str, column: str) -> None:
        self.get_table(table).create_index(column)

    def save_table(self, name: str, path: str, encoding: str = "utf-8") -> None:
        self.get_table(name).to_csv(path, encoding)

    def list_tables(self):
        return [table.name for table in self.tables.values()]

    def query(self, sql: str):
        return self.query_engine.execute(sql)
