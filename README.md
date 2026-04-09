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

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
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

### Query Syntax
The query engine supports basic SQL-like queries:
- `SELECT`: Choose specific columns
- `FROM`: Specify the table
- `WHERE`: Filter conditions
- `ORDER BY`: Sort results
- `GROUP BY`: Group results (if implemented)

## Implementation Details
- **Time Complexity**: O(n) for linear scans, O(log n) for indexed searches
- **Space Complexity**: O(n) for storing CSV data in memory
- **Data Structures**: Lists, dictionaries for efficient lookups and filtering

## Testing
Run the test suite:
```bash
python -m pytest tests/
```

## Authors
CS351 Project B

## License
This is an educational project for CS351.