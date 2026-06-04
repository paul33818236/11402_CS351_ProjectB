"""In-memory table storage for csvdb."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence


def infer_value(value: str) -> Any:
    """Convert a CSV string to a useful scalar value."""
    value = value.strip()
    if value == "":
        return None
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


class Table:
    """A table backed by a list of dictionaries."""

    def __init__(self, name: str, columns: Sequence[str], rows: Optional[Iterable[Mapping[str, Any]]] = None):
        if not columns:
            raise ValueError("A table must have at least one column")
        if len(set(column.lower() for column in columns)) != len(columns):
            raise ValueError("Column names must be unique (case-insensitive)")

        self.name = name
        self.columns = list(columns)
        self._column_names = {column.lower(): column for column in self.columns}
        self.rows: List[Dict[str, Any]] = []
        self.indexes: Dict[str, Dict[Any, List[int]]] = {}
        for row in rows or []:
            self.insert(row)

    @classmethod
    def from_csv(cls, name: str, path: str, encoding: str = "utf-8-sig") -> "Table":
        csv_path = Path(path)
        with csv_path.open("r", newline="", encoding=encoding) as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(f"CSV file has no header: {path}")
            rows = [
                {column: infer_value(value or "") for column, value in row.items()}
                for row in reader
            ]
        return cls(name, reader.fieldnames, rows)

    def resolve_column(self, column: str) -> str:
        try:
            return self._column_names[column.lower()]
        except KeyError:
            raise KeyError(f"Unknown column '{column}' in table '{self.name}'")

    def insert(self, row: Mapping[str, Any]) -> Dict[str, Any]:
        supplied = {key.lower(): value for key, value in row.items()}
        unknown = set(supplied) - set(self._column_names)
        if unknown:
            raise KeyError(f"Unknown column(s): {', '.join(sorted(unknown))}")
        normalized = {
            column: supplied.get(column.lower())
            for column in self.columns
        }
        self.rows.append(normalized)
        row_number = len(self.rows) - 1
        for column, index in self.indexes.items():
            index[normalized[column]].append(row_number)
        return normalized

    def create_index(self, column: str) -> None:
        column = self.resolve_column(column)
        index: Dict[Any, List[int]] = defaultdict(list)
        for row_number, row in enumerate(self.rows):
            index[row[column]].append(row_number)
        self.indexes[column] = index

    def drop_index(self, column: str) -> None:
        self.indexes.pop(self.resolve_column(column), None)

    def find(self, column: str, value: Any) -> List[Dict[str, Any]]:
        column = self.resolve_column(column)
        if column in self.indexes:
            return [self.rows[number] for number in self.indexes[column].get(value, [])]
        return [row for row in self.rows if row[column] == value]

    def to_csv(self, path: str, encoding: str = "utf-8") -> None:
        with Path(path).open("w", newline="", encoding=encoding) as handle:
            writer = csv.DictWriter(handle, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(self.rows)

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self.rows)

