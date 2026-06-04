"""Parser and executor for the csvdb SQL subset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cmp_to_key
from typing import Any, List, Optional, Sequence, Tuple


class QueryError(ValueError):
    """Raised when a query cannot be parsed or executed."""


TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<number>\d+(?:\.\d+)?)
      | (?P<string>'(?:''|[^'])*'|"(?:\"\"|[^"])*")
      | (?P<operator><=|>=|<>|!=|=|<|>)
      | (?P<punct>[(),*;])
      | (?P<identifier>[A-Za-z_][A-Za-z0-9_.]*)
      | (?P<bad>.)
    )
    """,
    re.VERBOSE,
)


def _compare(left: Any, operator: str, right: Any) -> bool:
    if operator in ("=", "=="):
        return left == right
    if operator in ("!=", "<>"):
        return left != right
    if left is None or right is None:
        return False
    try:
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
    except TypeError:
        left, right = str(left), str(right)
        return _compare(left, operator, right)
    raise QueryError(f"Unsupported operator '{operator}'")


class Expression:
    def evaluate(self, row, table):
        raise NotImplementedError


@dataclass
class Literal(Expression):
    value: Any

    def evaluate(self, row, table):
        return self.value


@dataclass
class Column(Expression):
    name: str

    def evaluate(self, row, table):
        name = self.name.split(".")[-1]
        return row[table.resolve_column(name)]


@dataclass
class Comparison(Expression):
    left: Expression
    operator: str
    right: Expression

    def evaluate(self, row, table):
        return _compare(
            self.left.evaluate(row, table),
            self.operator,
            self.right.evaluate(row, table),
        )


@dataclass
class Logical(Expression):
    left: Expression
    operator: str
    right: Expression

    def evaluate(self, row, table):
        if self.operator == "AND":
            return bool(self.left.evaluate(row, table)) and bool(self.right.evaluate(row, table))
        return bool(self.left.evaluate(row, table)) or bool(self.right.evaluate(row, table))


@dataclass
class Negation(Expression):
    expression: Expression

    def evaluate(self, row, table):
        return not bool(self.expression.evaluate(row, table))


@dataclass
class IsNull(Expression):
    expression: Expression
    negate: bool

    def evaluate(self, row, table):
        result = self.expression.evaluate(row, table) is None
        return not result if self.negate else result


@dataclass
class InList(Expression):
    expression: Expression
    values: Sequence[Expression]
    negate: bool

    def evaluate(self, row, table):
        result = self.expression.evaluate(row, table) in [
            value.evaluate(row, table) for value in self.values
        ]
        return not result if self.negate else result


@dataclass
class Like(Expression):
    expression: Expression
    pattern: Expression
    negate: bool

    def evaluate(self, row, table):
        value = self.expression.evaluate(row, table)
        pattern = self.pattern.evaluate(row, table)
        if value is None or pattern is None:
            return False
        regex = "^" + re.escape(str(pattern)).replace("%", ".*").replace("_", ".") + "$"
        result = re.match(regex, str(value), re.IGNORECASE) is not None
        return not result if self.negate else result


@dataclass
class SelectItem:
    column: Optional[str] = None
    aggregate: Optional[str] = None
    alias: Optional[str] = None
    star: bool = False

    @property
    def output_name(self) -> str:
        if self.alias:
            return self.alias
        if self.star:
            return "*"
        if self.aggregate:
            return f"{self.aggregate}({self.column or '*'})"
        return self.column or ""


@dataclass
class OrderItem:
    name: str
    descending: bool = False


@dataclass
class ParsedQuery:
    select: List[SelectItem]
    table: str
    where: Optional[Expression]
    group_by: List[str]
    order_by: List[OrderItem]
    limit: Optional[int]


class Parser:
    CLAUSES = {"FROM", "WHERE", "GROUP", "ORDER", "LIMIT"}
    AGGREGATES = {"COUNT", "SUM", "AVG", "MIN", "MAX"}

    def __init__(self, sql: str):
        self.tokens = self._tokenize(sql)
        self.position = 0

    @staticmethod
    def _tokenize(sql: str) -> List[Tuple[str, str]]:
        sql = sql.strip()
        tokens = []
        position = 0
        while position < len(sql):
            match = TOKEN_RE.match(sql, position)
            if not match:
                raise QueryError(f"Cannot parse query near: {sql[position:]}")
            position = match.end()
            kind = match.lastgroup
            value = match.group(kind)
            if kind == "bad":
                raise QueryError(f"Unexpected character '{value}'")
            tokens.append((kind, value))
        return tokens

    def peek(self, value: Optional[str] = None) -> bool:
        if self.position >= len(self.tokens):
            return False
        return value is None or self.tokens[self.position][1].upper() == value.upper()

    def take(self, value: Optional[str] = None) -> Tuple[str, str]:
        if not self.peek():
            raise QueryError("Unexpected end of query")
        token = self.tokens[self.position]
        if value is not None and token[1].upper() != value.upper():
            raise QueryError(f"Expected '{value}', got '{token[1]}'")
        self.position += 1
        return token

    def identifier(self) -> str:
        kind, value = self.take()
        if kind != "identifier":
            raise QueryError(f"Expected an identifier, got '{value}'")
        return value

    def parse(self) -> ParsedQuery:
        self.take("SELECT")
        select = self.parse_select()
        self.take("FROM")
        table = self.identifier()
        where = None
        group_by: List[str] = []
        order_by: List[OrderItem] = []
        limit = None
        if self.peek("WHERE"):
            self.take()
            where = self.parse_or()
        if self.peek("GROUP"):
            self.take()
            self.take("BY")
            group_by = self.parse_identifier_list()
        if self.peek("ORDER"):
            self.take()
            self.take("BY")
            order_by = self.parse_order()
        if self.peek("LIMIT"):
            self.take()
            kind, value = self.take()
            if kind != "number" or "." in value:
                raise QueryError("LIMIT must be a non-negative integer")
            limit = int(value)
        if self.peek(";"):
            self.take()
        if self.peek():
            raise QueryError(f"Unexpected token '{self.take()[1]}'")
        return ParsedQuery(select, table, where, group_by, order_by, limit)

    def parse_select(self) -> List[SelectItem]:
        items = []
        while True:
            if self.peek("*"):
                self.take()
                item = SelectItem(star=True)
            else:
                name = self.identifier()
                if name.upper() in self.AGGREGATES and self.peek("("):
                    aggregate = name.upper()
                    self.take("(")
                    column = None if self.peek("*") else self.identifier()
                    if self.peek("*"):
                        self.take()
                    self.take(")")
                    item = SelectItem(column=column, aggregate=aggregate)
                else:
                    item = SelectItem(column=name)
            if self.peek("AS"):
                self.take()
                item.alias = self.identifier()
            items.append(item)
            if not self.peek(","):
                break
            self.take()
        return items

    def parse_identifier_list(self) -> List[str]:
        values = [self.identifier()]
        while self.peek(","):
            self.take()
            values.append(self.identifier())
        return values

    def parse_order(self) -> List[OrderItem]:
        items = []
        while True:
            name = self.identifier()
            descending = False
            if self.peek("ASC") or self.peek("DESC"):
                descending = self.take()[1].upper() == "DESC"
            items.append(OrderItem(name, descending))
            if not self.peek(","):
                return items
            self.take()

    def parse_or(self) -> Expression:
        expression = self.parse_and()
        while self.peek("OR"):
            self.take()
            expression = Logical(expression, "OR", self.parse_and())
        return expression

    def parse_and(self) -> Expression:
        expression = self.parse_not()
        while self.peek("AND"):
            self.take()
            expression = Logical(expression, "AND", self.parse_not())
        return expression

    def parse_not(self) -> Expression:
        if self.peek("NOT"):
            self.take()
            return Negation(self.parse_not())
        return self.parse_predicate()

    def parse_predicate(self) -> Expression:
        if self.peek("("):
            self.take()
            expression = self.parse_or()
            self.take(")")
            return expression
        left = self.parse_operand()
        if self.peek("IS"):
            self.take()
            negate = False
            if self.peek("NOT"):
                self.take()
                negate = True
            self.take("NULL")
            return IsNull(left, negate)
        negate = False
        if self.peek("NOT"):
            self.take()
            negate = True
        if self.peek("IN"):
            self.take()
            self.take("(")
            values = [self.parse_operand()]
            while self.peek(","):
                self.take()
                values.append(self.parse_operand())
            self.take(")")
            return InList(left, values, negate)
        if self.peek("LIKE"):
            self.take()
            return Like(left, self.parse_operand(), negate)
        if negate:
            raise QueryError("Expected IN or LIKE after NOT")
        kind, operator = self.take()
        if kind != "operator":
            raise QueryError(f"Expected comparison operator, got '{operator}'")
        return Comparison(left, operator, self.parse_operand())

    def parse_operand(self) -> Expression:
        kind, value = self.take()
        if kind == "string":
            quote = value[0]
            return Literal(value[1:-1].replace(quote * 2, quote))
        if kind == "number":
            return Literal(float(value) if "." in value else int(value))
        if kind != "identifier":
            raise QueryError(f"Expected a value, got '{value}'")
        upper = value.upper()
        if upper == "NULL":
            return Literal(None)
        if upper == "TRUE":
            return Literal(True)
        if upper == "FALSE":
            return Literal(False)
        return Column(value)


class QueryEngine:
    """Execute parsed SELECT statements against a Database."""

    def __init__(self, database):
        self.database = database

    def execute(self, sql: str):
        query = Parser(sql).parse()
        table = self.database.get_table(query.table)
        rows = self._candidate_rows(table, query.where)
        if query.where:
            rows = [row for row in rows if query.where.evaluate(row, table)]

        aggregate_query = any(item.aggregate for item in query.select)
        if query.group_by or aggregate_query:
            results = self._aggregate(rows, table, query)
        else:
            results = self._project(rows, table, query.select)
        results = self._sort(results, query.order_by)
        return results[: query.limit] if query.limit is not None else results

    @staticmethod
    def _candidate_rows(table, expression):
        if isinstance(expression, Comparison) and expression.operator == "=":
            if isinstance(expression.left, Column) and isinstance(expression.right, Literal):
                return table.find(expression.left.name.split(".")[-1], expression.right.value)
            if isinstance(expression.right, Column) and isinstance(expression.left, Literal):
                return table.find(expression.right.name.split(".")[-1], expression.left.value)
        return list(table)

    @staticmethod
    def _project(rows, table, select):
        if len(select) == 1 and select[0].star:
            return [row.copy() for row in rows]
        if any(item.star for item in select):
            raise QueryError("'*' cannot be combined with other selected columns")
        results = []
        for row in rows:
            result = {}
            for item in select:
                column = table.resolve_column(item.column.split(".")[-1])
                result[item.output_name] = row[column]
            results.append(result)
        return results

    def _aggregate(self, rows, table, query):
        if any(item.star and not item.aggregate for item in query.select):
            raise QueryError("SELECT * is not supported in aggregate queries")
        group_columns = [table.resolve_column(name.split(".")[-1]) for name in query.group_by]
        groups = {}
        for row in rows:
            key = tuple(row[column] for column in group_columns)
            groups.setdefault(key, []).append(row)
        if not group_columns and not groups:
            groups[()] = []

        results = []
        for group_rows in groups.values():
            result = {}
            for item in query.select:
                if item.aggregate:
                    result[item.output_name] = self._aggregate_value(item, group_rows, table)
                else:
                    column = table.resolve_column(item.column.split(".")[-1])
                    if column not in group_columns:
                        raise QueryError(f"Selected column '{item.column}' must appear in GROUP BY")
                    result[item.output_name] = group_rows[0][column]
            results.append(result)
        return results

    @staticmethod
    def _aggregate_value(item, rows, table):
        if item.aggregate == "COUNT" and item.column is None:
            return len(rows)
        column = table.resolve_column(item.column.split(".")[-1])
        values = [row[column] for row in rows if row[column] is not None]
        if item.aggregate == "COUNT":
            return len(values)
        if item.aggregate == "SUM":
            return sum(values)
        if item.aggregate == "AVG":
            return sum(values) / len(values) if values else None
        if item.aggregate == "MIN":
            return min(values) if values else None
        if item.aggregate == "MAX":
            return max(values) if values else None
        raise QueryError(f"Unknown aggregate '{item.aggregate}'")

    @staticmethod
    def _sort(results, order_by):
        if not order_by:
            return results

        def lookup(row, name):
            lowered = name.lower()
            for key, value in row.items():
                if key.lower() == lowered:
                    return value
            raise QueryError(f"ORDER BY column '{name}' is not in the result")

        def compare(left, right):
            for item in order_by:
                a, b = lookup(left, item.name), lookup(right, item.name)
                if a == b:
                    continue
                if a is None:
                    result = 1
                elif b is None:
                    result = -1
                else:
                    try:
                        result = -1 if a < b else 1
                    except TypeError:
                        result = -1 if str(a) < str(b) else 1
                return -result if item.descending else result
            return 0

        return sorted(results, key=cmp_to_key(compare))
