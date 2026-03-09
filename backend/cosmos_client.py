"""Cosmos DB client for retrieving code examples used in RAG.

Queries the Azure Cosmos DB container to retrieve Python code examples
filtered by language. The container schema has these fields per the specification:
- "type": "good" or "bad"
- "language": programming language of the example
- "severity": "low", "medium", or "high"
- "description": explanation of the example
- "code": the code snippet
"""

from azure.cosmos import CosmosClient, ContainerProxy

from backend.config import (
    COSMOS_ENDPOINT,
    COSMOS_KEY,
    COSMOS_DATABASE_NAME,
    COSMOS_CONTAINER_NAME,
)


def _get_container() -> ContainerProxy:
    client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
    database = client.get_database_client(COSMOS_DATABASE_NAME)
    return database.get_container_client(COSMOS_CONTAINER_NAME)


def retrieve_python_examples() -> list[dict]:
    """Retrieve all Python code examples from Cosmos DB.

    As specified, only Python examples are used for RAG even though
    the database may contain examples in other languages.

    Returns:
        List of code example documents with type, severity, description, code.
    """
    container = _get_container()
    query = (
        "SELECT c.type, c.language, c.severity, c.description, c.code "
        "FROM c WHERE c.language = @language"
    )
    parameters: list[dict] = [{"name": "@language", "value": "Python"}]
    items = list(
        container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True,
        )
    )
    return items


def retrieve_examples_by_type(example_type: str) -> list[dict]:
    """Retrieve Python code examples filtered by type ('good' or 'bad').

    Args:
        example_type: Either 'good' or 'bad'.

    Returns:
        List of matching code example documents.
    """
    container = _get_container()
    query = (
        "SELECT c.type, c.language, c.severity, c.description, c.code "
        "FROM c WHERE c.language = @language AND c.type = @type"
    )
    parameters: list[dict] = [
        {"name": "@language", "value": "Python"},
        {"name": "@type", "value": example_type},
    ]
    items = list(
        container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True,
        )
    )
    return items


def format_examples_for_context(examples: list[dict]) -> str:
    """Format retrieved code examples into a text block for agent context.

    Args:
        examples: List of code example documents from Cosmos DB.

    Returns:
        Formatted string suitable for including in agent instructions.
    """
    sections: list[str] = []
    for i, ex in enumerate(examples, start=1):
        sections.append(
            f"--- Example {i} ---\n"
            f"Type: {ex['type']}\n"
            f"Severity: {ex.get('severity', 'N/A')}\n"
            f"Description: {ex['description']}\n"
            f"Code:\n{ex['code']}\n"
        )
    return "\n".join(sections)
