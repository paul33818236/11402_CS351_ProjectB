# CSV Mini Database & Query Engine

## Overview
A lightweight CSV-based mini database system with query engine capabilities. This project implements core database functionality including data storage, retrieval, filtering, and querying on CSV files.

## Features
- **CSV Data Management**: Read, parse, and manage CSV files as database tables
- **Query Engine**: Execute SQL-like queries on CSV data
- **Data Filtering**: Filter records based on conditions
- **Data Sorting**: Sort results by specified columns
- **Aggregation**: Support for basic aggregation operations
- **Indexing**: Efficient data retrieval with index support

## Project Structure
```
11402_CS351_ProjectB/
├── README.md              # This file
├── src/                   # Source code
│   ├── csvdb/
│   │   ├── database.py    # Main database engine
│   │   ├── query.py       # Query parser and executor
│   │   └── table.py       # Table data structure
│   └── main.py            # Entry point
├── tests/                 # Test files
├── data/                  # Sample CSV files for testing
└── requirements.txt       # Python dependencies
```

## Requirements
- Python 3.7+
- Standard library only (no external dependencies)

## Installation
1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd 11402_CS351_ProjectB
   ```

2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package (there are no third-party runtime dependencies):
   ```bash
   pip install -e .
   ```

## Usage
### Basic Example
```python
from csvdb import Database

# Create or load a database
db = Database()

# Load CSV file
db.load_table('students', 'data/students.csv')

# Query data
results = db.query("SELECT * FROM students WHERE grade > 80")
```

Results are returned as a list of dictionaries. CSV values are automatically
converted to integers, floats, booleans, or `None` when possible.

### Command Line
```bash
python src/main.py --table students=data/students.csv --query "SELECT department, AVG(grade) AS average FROM students GROUP BY department"
```

Omit `--query` to start an interactive query prompt. Repeat `--table NAME=PATH`
to load more than one table.

### Query Syntax
The query engine supports basic SQL-like queries:
- `SELECT`: Choose specific columns
- `FROM`: Specify the table
- `WHERE`: Filter conditions
- `ORDER BY`: Sort results
- `GROUP BY`: Group results
- `LIMIT`: Limit the number of returned records

Supported predicates include `=`, `!=`, `<>`, `<`, `<=`, `>`, `>=`, `AND`,
`OR`, `NOT`, `IN`, `LIKE`, `IS NULL`, and `IS NOT NULL`. Supported aggregate
functions are `COUNT`, `SUM`, `AVG`, `MIN`, and `MAX`.

### Indexes and Saving
```python
db.create_index("students", "id")
db.save_table("students", "data/students-copy.csv")
```

## Implementation Details
- **Time Complexity**: O(n) for linear scans, O(log n) for indexed searches
- **Space Complexity**: O(n) for storing CSV data in memory
- **Data Structures**: Lists, dictionaries for efficient lookups and filtering

## Testing
Run the test suite:
```bash
python -m unittest discover -s tests
```

## Authors
CS351 Project B

## License
This is an educational project for CS351.
