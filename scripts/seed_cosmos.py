"""Seed the Cosmos DB container with sample Python code examples.

Usage:
    python scripts/seed_cosmos.py

Requires environment variables (or .env file):
    COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE_NAME, COSMOS_CONTAINER_NAME
"""

import os
import sys
import uuid

from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError

load_dotenv()

COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
COSMOS_DATABASE_NAME = os.environ.get("COSMOS_DATABASE_NAME", "code-examples")
COSMOS_CONTAINER_NAME = os.environ.get("COSMOS_CONTAINER_NAME", "examples")

# ---------------------------------------------------------------------------
# Sample code examples
#
# Each entry follows the Cosmos DB schema:
#   type:        "good" | "bad"
#   language:    programming language
#   severity:    "low" | "medium" | "high"
#   description: explanation of what is good or bad
#   code:        the code snippet
# ---------------------------------------------------------------------------

SAMPLES: list[dict] = [
    # ---- GOOD examples ----
    {
        "type": "good",
        "language": "Python",
        "severity": "low",
        "description": "Uses descriptive variable names and follows PEP 8 naming conventions.",
        "code": (
            "def calculate_total_price(unit_price: float, quantity: int, tax_rate: float) -> float:\n"
            "    subtotal = unit_price * quantity\n"
            "    tax_amount = subtotal * tax_rate\n"
            "    return subtotal + tax_amount\n"
        ),
    },
    {
        "type": "good",
        "language": "Python",
        "severity": "low",
        "description": "Properly uses type hints and returns clear types.",
        "code": (
            "from typing import Optional\n\n\n"
            "def find_user_by_email(email: str, users: list[dict]) -> Optional[dict]:\n"
            "    for user in users:\n"
            "        if user.get('email') == email:\n"
            "            return user\n"
            "    return None\n"
        ),
    },
    {
        "type": "good",
        "language": "Python",
        "severity": "medium",
        "description": "Handles known file-not-found error with a specific exception and informative message.",
        "code": (
            "import logging\n\n"
            "logger = logging.getLogger(__name__)\n\n\n"
            "def read_config(path: str) -> str:\n"
            "    try:\n"
            "        with open(path, 'r', encoding='utf-8') as f:\n"
            "            return f.read()\n"
            "    except FileNotFoundError:\n"
            "        logger.error('Configuration file not found: %s', path)\n"
            "        raise\n"
        ),
    },
    {
        "type": "good",
        "language": "Python",
        "severity": "medium",
        "description": "Uses a broad try/except as a fallback with logging for unknown errors.",
        "code": (
            "import logging\n\n"
            "logger = logging.getLogger(__name__)\n\n\n"
            "def process_request(data: dict) -> dict:\n"
            "    try:\n"
            "        result = transform(data)\n"
            "        return {'status': 'ok', 'result': result}\n"
            "    except ValueError as exc:\n"
            "        logger.warning('Validation error: %s', exc)\n"
            "        return {'status': 'error', 'detail': str(exc)}\n"
            "    except Exception:\n"
            "        logger.exception('Unexpected error processing request')\n"
            "        return {'status': 'error', 'detail': 'An unexpected error occurred.'}\n"
        ),
    },
    {
        "type": "good",
        "language": "Python",
        "severity": "high",
        "description": "Validates input at system boundary and raises clear ValueError for bad input.",
        "code": (
            "def create_user(name: str, age: int) -> dict:\n"
            "    if not name or not name.strip():\n"
            "        raise ValueError('name must be a non-empty string')\n"
            "    if age < 0 or age > 150:\n"
            "        raise ValueError(f'age must be between 0 and 150, got {age}')\n"
            "    return {'name': name.strip(), 'age': age}\n"
        ),
    },
    {
        "type": "good",
        "language": "Python",
        "severity": "low",
        "description": "Correct list comprehension with clear logic and edge case handling.",
        "code": (
            "def get_even_numbers(numbers: list[int]) -> list[int]:\n"
            "    if not numbers:\n"
            "        return []\n"
            "    return [n for n in numbers if n % 2 == 0]\n"
        ),
    },
    {
        "type": "good",
        "language": "Python",
        "severity": "medium",
        "description": "Uses context managers and handles resource cleanup correctly.",
        "code": (
            "import sqlite3\n\n\n"
            "def fetch_users(db_path: str) -> list[tuple]:\n"
            "    with sqlite3.connect(db_path) as conn:\n"
            "        cursor = conn.cursor()\n"
            "        cursor.execute('SELECT id, name FROM users')\n"
            "        return cursor.fetchall()\n"
        ),
    },
    {
        "type": "good",
        "language": "Python",
        "severity": "high",
        "description": "Defensive programming with comprehensive logging for resilience against unknown errors.",
        "code": (
            "import logging\n"
            "import traceback\n\n"
            "logger = logging.getLogger(__name__)\n\n\n"
            "def safe_divide(a: float, b: float) -> float | None:\n"
            "    try:\n"
            "        return a / b\n"
            "    except ZeroDivisionError:\n"
            "        logger.error('Division by zero: a=%s, b=%s', a, b)\n"
            "        return None\n"
            "    except TypeError as exc:\n"
            "        logger.error('Invalid types for division: %s', exc)\n"
            "        return None\n"
            "    except Exception:\n"
            "        logger.critical('Unexpected error in safe_divide:\\n%s', traceback.format_exc())\n"
            "        return None\n"
        ),
    },
    # ---- BAD examples ----
    {
        "type": "bad",
        "language": "Python",
        "severity": "high",
        "description": "Uses bare except which silently swallows all errors including SystemExit and KeyboardInterrupt.",
        "code": (
            "def load_data(path):\n"
            "    try:\n"
            "        f = open(path)\n"
            "        data = f.read()\n"
            "        f.close()\n"
            "        return data\n"
            "    except:\n"
            "        pass\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "medium",
        "description": "Single-character variable names make the code difficult to understand.",
        "code": (
            "def f(x, y, z):\n"
            "    a = x * y\n"
            "    b = a + z\n"
            "    return b\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "medium",
        "description": "No error handling for file operations; will crash on missing file or permission error.",
        "code": (
            "def read_file(path):\n"
            "    with open(path) as f:\n"
            "        return f.read()\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "high",
        "description": "SQL injection vulnerability via string formatting instead of parameterized queries.",
        "code": (
            "import sqlite3\n\n\n"
            "def get_user(name):\n"
            "    conn = sqlite3.connect('db.sqlite')\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute(f\"SELECT * FROM users WHERE name = '{name}'\")\n"
            "    return cursor.fetchone()\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "low",
        "description": "Inconsistent indentation mixing tabs and spaces, violating PEP 8.",
        "code": (
            "def greet(name):\n"
            "\tif name:\n"
            "        print('Hello ' + name)\n"
            "\telse:\n"
            "        print('Hello')\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "medium",
        "description": "Mutable default argument; the list is shared across all calls.",
        "code": (
            "def append_value(value, items=[]):\n"
            "    items.append(value)\n"
            "    return items\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "high",
        "description": "No handling of unknown errors; any unexpected exception crashes the application.",
        "code": (
            "import json\n\n\n"
            "def parse_and_sum(json_string):\n"
            "    data = json.loads(json_string)\n"
            "    total = 0\n"
            "    for item in data['values']:\n"
            "        total += item\n"
            "    return total\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "medium",
        "description": "Catches exception but does nothing; errors are invisible to callers and logs.",
        "code": (
            "def connect_to_service(url):\n"
            "    try:\n"
            "        response = requests.get(url)\n"
            "        return response.json()\n"
            "    except Exception as e:\n"
            "        return None\n"
        ),
    },
    {
        "type": "bad",
        "language": "Python",
        "severity": "high",
        "description": "Function returns inconsistent types (dict or string), making caller logic fragile.",
        "code": (
            "def get_result(success):\n"
            "    if success:\n"
            "        return {'data': 42}\n"
            "    return 'error'\n"
        ),
    },
    # ---- Non-Python examples (should be ignored by the RAG filter) ----
    {
        "type": "good",
        "language": "JavaScript",
        "severity": "low",
        "description": "Uses const and arrow functions following modern JS conventions.",
        "code": (
            "const add = (a, b) => a + b;\n"
        ),
    },
    {
        "type": "bad",
        "language": "Java",
        "severity": "medium",
        "description": "Catches generic Exception instead of specific types.",
        "code": (
            "public void process() {\n"
            "    try {\n"
            "        doWork();\n"
            "    } catch (Exception e) {\n"
            "        // swallowed\n"
            "    }\n"
            "}\n"
        ),
    },
]


def seed() -> None:
    client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)

    # Ensure database exists
    database = client.create_database_if_not_exists(id=COSMOS_DATABASE_NAME)

    # Ensure container exists (partition key: /language)
    container = database.create_container_if_not_exists(
        id=COSMOS_CONTAINER_NAME,
        partition_key=PartitionKey(path="/language"),
    )

    created = 0
    skipped = 0

    for sample in SAMPLES:
        doc = dict(sample)
        doc["id"] = str(uuid.uuid4())
        try:
            container.create_item(body=doc)
            created += 1
            print(f"  Created: [{doc['language']}] [{doc['type']}] {doc['description'][:60]}")
        except CosmosResourceExistsError:
            skipped += 1

    print(f"\nDone. Created {created} items, skipped {skipped}.")


if __name__ == "__main__":
    print(f"Seeding Cosmos DB: {COSMOS_ENDPOINT}")
    print(f"  Database:  {COSMOS_DATABASE_NAME}")
    print(f"  Container: {COSMOS_CONTAINER_NAME}")
    print()
    seed()
