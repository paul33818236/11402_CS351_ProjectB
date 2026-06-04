import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from csvdb import Database, QueryError, Table


class CsvDbTests(unittest.TestCase):
    def setUp(self):
        self.database = Database()
        self.database.create_table(
            "students",
            ["id", "name", "grade", "department", "active"],
            [
                {"id": 1, "name": "Alice", "grade": 91, "department": "CS", "active": True},
                {"id": 2, "name": "Bob", "grade": 78, "department": "Math", "active": True},
                {"id": 3, "name": "Carla", "grade": 85, "department": "CS", "active": False},
                {"id": 4, "name": "David", "grade": 91, "department": "Math", "active": True},
                {"id": 5, "name": "Eve", "grade": None, "department": "CS", "active": True},
            ],
        )

    def test_load_csv_and_infer_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "values.csv"
            path.write_text("id,score,active,note\n1,8.5,true,\n", encoding="utf-8")
            table = Table.from_csv("values", str(path))
        self.assertEqual(table.rows, [{"id": 1, "score": 8.5, "active": True, "note": None}])

    def test_select_where_order_and_limit(self):
        result = self.database.query(
            "SELECT name, grade FROM students "
            "WHERE grade >= 85 AND department = 'CS' ORDER BY grade DESC, name LIMIT 2;"
        )
        self.assertEqual(result, [{"name": "Alice", "grade": 91}, {"name": "Carla", "grade": 85}])

    def test_boolean_predicates_and_like(self):
        result = self.database.query(
            "SELECT name FROM students "
            "WHERE (department IN ('CS', 'Art') AND name LIKE 'C%') OR grade IS NULL"
        )
        self.assertEqual(result, [{"name": "Carla"}, {"name": "Eve"}])

    def test_aggregates_and_grouping(self):
        result = self.database.query(
            "SELECT department, COUNT(*) AS total, AVG(grade) AS average "
            "FROM students GROUP BY department ORDER BY department"
        )
        self.assertEqual(
            result,
            [
                {"department": "CS", "total": 3, "average": 88.0},
                {"department": "Math", "total": 2, "average": 84.5},
            ],
        )

    def test_index_tracks_insertions(self):
        table = self.database.get_table("students")
        self.database.create_index("students", "department")
        table.insert({"id": 6, "name": "Finn", "grade": 80, "department": "CS", "active": True})
        self.assertEqual(
            [row["name"] for row in table.find("department", "CS")],
            ["Alice", "Carla", "Eve", "Finn"],
        )

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "students.csv"
            self.database.save_table("students", str(path))
            loaded = Database()
            loaded.load_table("students", str(path))
            result = loaded.query("SELECT COUNT(*) AS count FROM students")
        self.assertEqual(result, [{"count": 5}])

    def test_invalid_grouped_column_is_rejected(self):
        with self.assertRaisesRegex(QueryError, "GROUP BY"):
            self.database.query("SELECT name, COUNT(*) FROM students GROUP BY department")


if __name__ == "__main__":
    unittest.main()
