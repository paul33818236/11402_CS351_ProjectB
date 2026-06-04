"""Command-line interface for csvdb."""

from __future__ import annotations

import argparse
import json
import sys

from csvdb import Database, QueryError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query CSV files with a small SQL dialect")
    parser.add_argument(
        "--table",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="load a CSV as a named table (repeatable)",
    )
    parser.add_argument("--query", "-q", help="execute one query; otherwise start an interactive prompt")
    return parser


def load_tables(database: Database, definitions) -> None:
    for definition in definitions:
        if "=" not in definition:
            raise ValueError(f"Invalid table definition '{definition}'; expected NAME=PATH")
        name, path = definition.split("=", 1)
        database.load_table(name, path)


def print_results(results) -> None:
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))


def interactive(database: Database) -> None:
    print(f"Loaded tables: {', '.join(database.list_tables()) or '(none)'}")
    print("Enter a SELECT query, or 'quit' to exit.")
    while True:
        try:
            sql = input("csvdb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if sql.lower() in {"quit", "exit"}:
            return
        if not sql:
            continue
        try:
            print_results(database.query(sql))
        except (QueryError, KeyError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    database = Database()
    try:
        load_tables(database, args.table)
        if args.query:
            print_results(database.query(args.query))
        else:
            interactive(database)
        return 0
    except (OSError, QueryError, KeyError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

